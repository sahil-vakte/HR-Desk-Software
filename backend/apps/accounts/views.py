import hashlib
import secrets
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, Throttled
from apps.core.models import AuditEvent
from apps.core.access import has_menu, reporting_manager
from .models import LoginAttempt, PasswordReset, User, MenuItem


def auth_event(user, action):
    AuditEvent.objects.create(actor=user, entity="accounts.user", entity_id=str(user.pk), action=action)


def throttle(request, prefix):
    key = hashlib.sha256((prefix + str(request.data.get("email", "")).strip().lower() + request.META.get("REMOTE_ADDR", "")).encode()).hexdigest()
    now = timezone.now()
    with transaction.atomic():
        row, _ = LoginAttempt.objects.select_for_update().get_or_create(key=key, defaults={"started_at": now})
        if row.started_at < now - timedelta(minutes=15):
            row.attempts, row.started_at = 0, now
        if row.attempts >= 5:
            raise Throttled(wait=900, detail="Too many attempts. Try again in 15 minutes.")
        row.attempts += 1
        row.save()
    return key


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        key = throttle(request, "login")
        user = authenticate(request, username=request.data.get("email", ""), password=request.data.get("password", ""))
        if user is None or not user.role_id or not user.role.status or user.role.is_deleted:
            raise ValidationError({"email": ["These credentials do not match our records."]})
        login(request, user)
        request.session["authenticated_at"] = timezone.now().timestamp()
        request.session["auth_version"] = user.auth_version
        LoginAttempt.objects.filter(key=key).delete()
        auth_event(user, "login")
        return Response({"message": "Signed in successfully."})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        auth_event(request.user, "logout")
        logout(request)
        return Response(status=204)


class SessionView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        user = request.user
        manager = reporting_manager(user)
        items = list(MenuItem.objects.filter(status=True, master_status=True).order_by("order", "pk"))
        granted = [item.pk for item in items if has_menu(user, item.pk)]
        visible = {item.pk: {"menu_id": item.pk, "label": item.title, "path": item.route, "children": []}
                   for item in items if item.is_menu and item.pk in granted and (item.pk != 46 or manager)}
        roots = []
        for item in items:
            if item.pk not in visible:
                continue
            node = visible[item.pk]
            if item.parent_id in visible:
                visible[item.parent_id]["children"].append(node)
            elif item.route or item.parent_id is None:
                roots.append(node)
        roots = [node for node in roots if node["path"] or node["children"]]
        if user.role_id == 1:
            roots.append({"menu_id": "administration", "label": "Administration", "path": "", "children": [
                {"menu_id": "users", "label": "Users", "path": "/admin/users"},
                {"menu_id": "roles", "label": "Roles", "path": "/admin/roles"},
                {"menu_id": "audit", "label": "Audit events", "path": "/audit-events"}]})
        return Response({"user": {"id": user.pk, "first_name": user.first_name, "last_name": user.last_name,
            "email": user.email, "role_id": user.role_id}, "permissions": granted, "menu": roots,
            "is_reporting_manager": manager})


@method_decorator(csrf_protect, name="dispatch")
class ForgotPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        throttle(request, "reset")
        user = User.objects.filter(email__iexact=request.data.get("email", ""), is_active=True, is_deleted=False).first()
        if user:
            token = secrets.token_urlsafe(48)
            PasswordReset.objects.create(user=user, digest=hashlib.sha256(token.encode()).hexdigest(), expires_at=timezone.now()+timedelta(hours=1))
            send_mail("Reset your HRDESK password", f"Reset your password: {settings.FRONTEND_ORIGIN}/reset-password/{token}\nThis single-use link expires in one hour.", settings.DEFAULT_FROM_EMAIL, [user.email])
            auth_event(user, "password_reset_requested")
        return Response({"message": "If the account exists, a reset link has been sent."})


@method_decorator(csrf_protect, name="dispatch")
class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    def post(self, request):
        with transaction.atomic():
            digest = hashlib.sha256(str(request.data.get("token", "")).encode()).hexdigest()
            reset = PasswordReset.objects.select_for_update().filter(digest=digest, consumed_at=None, expires_at__gt=timezone.now()).first()
            if not reset:
                raise ValidationError({"token": ["This reset link is invalid or expired."]})
            password = request.data.get("password", "")
            if password != request.data.get("confirm_password"):
                raise ValidationError({"confirm_password": ["Passwords do not match."]})
            validate_password(password, reset.user)
            reset.user.set_password(password)
            reset.user.auth_version += 1
            reset.user.save()
            reset.consumed_at = timezone.now()
            reset.save()
            auth_event(reset.user, "password_reset")
        return Response({"message": "Password reset successfully."})


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        user = request.user
        if not user.check_password(request.data.get("old_password", "")):
            raise ValidationError({"old_password": ["The current password is incorrect."]})
        password = request.data.get("password", "")
        if password != request.data.get("confirm_password"):
            raise ValidationError({"confirm_password": ["Passwords do not match."]})
        validate_password(password, user)
        with transaction.atomic():
            user.set_password(password)
            user.auth_version += 1
            user.save()
            update_session_auth_hash(request, user)
            request.session["auth_version"] = user.auth_version
            auth_event(user, "password_changed")
        return Response({"message": "Password changed successfully."})
