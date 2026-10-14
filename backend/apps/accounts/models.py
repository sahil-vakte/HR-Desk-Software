from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from apps.core.models import BaseModel


class Role(BaseModel):
    title = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)


class MenuItem(BaseModel):
    title = models.CharField(max_length=150)
    slug = models.SlugField(max_length=150)
    route = models.CharField(max_length=200, blank=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT)
    is_menu = models.BooleanField(default=True)
    icon = models.CharField(max_length=100, blank=True)
    order = models.PositiveIntegerField(default=0)
    master_status = models.BooleanField(default=True)


class RolePermission(BaseModel):
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="grants")
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT)
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [models.UniqueConstraint(fields=["role", "menu_item"], name="unique_role_menu")]


class User(AbstractUser):
    email = models.EmailField(unique=True)
    role = models.ForeignKey(Role, null=True, on_delete=models.PROTECT)
    phone = models.CharField(max_length=40, blank=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    auth_version = models.PositiveIntegerField(default=0)
    class Meta:
        constraints = [models.UniqueConstraint(Lower("email"), name="unique_email_casefold")]


class LoginAttempt(models.Model):
    key = models.CharField(max_length=64, unique=True)
    attempts = models.PositiveIntegerField(default=0)
    started_at = models.DateTimeField()


class PasswordReset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
