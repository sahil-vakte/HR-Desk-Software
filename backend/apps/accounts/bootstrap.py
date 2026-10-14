"""Temporary administrator setup for test servers, including production mode."""
import secrets

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.db import IntegrityError, transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from apps.core.models import AuditEvent
from .models import Role, User


class BootstrapThrottle(SimpleRateThrottle):
    scope = "bootstrap_admin"
    rate = "5/hour"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class BootstrapInput(serializers.Serializer):
    email = serializers.EmailField(max_length=254)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(trim_whitespace=False, write_only=True)
    confirm_password = serializers.CharField(trim_whitespace=False, write_only=True)

    def validate(self, data):
        data["email"] = data["email"].lower()
        if data["password"] != data.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": ["Passwords do not match."]})
        user = User(username=data["email"], **data)
        validate_password(data["password"], user=user)
        return data


@method_decorator(csrf_protect, name="dispatch")
class BootstrapAdminView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [BootstrapThrottle]

    def post(self, request):
        if not settings.BOOTSTRAP_ADMIN_ENABLED:
            raise NotFound()
        expected = settings.BOOTSTRAP_ADMIN_TOKEN
        supplied = request.headers.get("X-Bootstrap-Token", "")
        if not expected or not secrets.compare_digest(expected.encode(), supplied.encode()):
            raise PermissionDenied()
        serializer = BootstrapInput(data=request.data)
        serializer.is_valid(raise_exception=True)
        role = Role.objects.filter(pk=1, status=True, is_deleted=False).first()
        if role is None:
            raise ValidationError({"non_field_errors": ["Run manage.py seed before creating an administrator."]})
        data = serializer.validated_data.copy()
        password = data.pop("password")
        try:
            with transaction.atomic():
                user = User(username=data["email"], role=role, is_staff=True, is_superuser=True, **data)
                user.set_password(password)
                user.save()
                AuditEvent.objects.create(actor=user, entity="accounts.user", entity_id=str(user.pk),
                                          action="administrator_created")
        except IntegrityError:
            raise ValidationError({"email": ["An account already exists for this email."]})
        return Response({"message": "Administrator created. You can now sign in."}, status=201)
