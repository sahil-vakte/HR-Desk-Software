from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone


class AuditQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise ValidationError("Audit events are append-only.")

    def delete(self):
        raise ValidationError("Audit events are append-only.")

    def bulk_update(self, objs, fields, **kwargs):
        raise ValidationError("Audit events are append-only.")


class AuditEvent(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    entity = models.CharField(max_length=120)
    entity_id = models.CharField(max_length=64)
    action = models.CharField(max_length=40)
    before = models.JSONField(default=dict)
    after = models.JSONField(default=dict)
    at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    objects = AuditQuerySet.as_manager()

    class Meta:
        ordering = ["-at", "-pk"]
        indexes = [models.Index(fields=["entity", "entity_id"], name="audit_entity_idx")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError("Audit events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events are append-only.")


class BusinessQuerySet(models.QuerySet):
    def delete(self):
        raise ValidationError("Use instance.delete(actor=...) for audited soft deletion.")

    def update(self, **kwargs):
        raise ValidationError("Use instance.save(actor=...) for audited changes.")

    def bulk_create(self, objs, **kwargs):
        raise ValidationError("Bulk writes bypass auditing and are disabled.")

    def bulk_update(self, objs, fields, **kwargs):
        raise ValidationError("Bulk writes bypass auditing and are disabled.")


class ActiveManager(models.Manager.from_queryset(BusinessQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.BooleanField(default=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    objects = ActiveManager()
    all_objects = BusinessQuerySet.as_manager()
    # Subclasses explicitly opt non-sensitive fields into audit snapshots.
    audit_fields = ("status", "is_deleted")

    class Meta:
        abstract = True
        base_manager_name = "all_objects"
        default_manager_name = "objects"
        constraints = [models.CheckConstraint(
            condition=Q(is_deleted=False, deleted_at__isnull=True) | Q(is_deleted=True, deleted_at__isnull=False),
            name="%(app_label)s_%(class)s_deletion_consistent",
        )]

    def audit_snapshot(self):
        import json
        from django.core.serializers.json import DjangoJSONEncoder
        excluded = {"password", "answers", "medical_condition", "driver_licence_number", "address", "bank_details", "number", "digest"}
        values = {field.attname: getattr(self, field.attname) for field in self._meta.fields
                  if field.name not in excluded and not isinstance(field, EncryptedTextField)}
        return json.loads(json.dumps(values, cls=DjangoJSONEncoder))

    def save(self, *args, actor=None, **kwargs):
        with transaction.atomic():
            prior = None if self._state.adding else type(self).all_objects.select_for_update().get(pk=self.pk)
            before = prior.audit_snapshot() if prior else {}
            super().save(*args, **kwargs)
            self.refresh_from_db()
            AuditEvent.objects.create(actor=actor, entity=self._meta.label_lower, entity_id=str(self.pk),
                                      action="create" if prior is None else "update",
                                      before=before, after=self.audit_snapshot())

    def delete(self, using=None, keep_parents=False, *, actor=None):
        with transaction.atomic():
            current = type(self).all_objects.select_for_update().get(pk=self.pk)
            if current.is_deleted:
                return (0, {})
            before = current.audit_snapshot()
            current.is_deleted = True
            current.deleted_at = timezone.now()
            models.Model.save(current, update_fields=["is_deleted", "deleted_at", "updated_at"])
            AuditEvent.objects.create(actor=actor, entity=self._meta.label_lower, entity_id=str(self.pk),
                                      action="delete", before=before, after=current.audit_snapshot())
            self.is_deleted, self.deleted_at = current.is_deleted, current.deleted_at
            return (1, {self._meta.label: 1})

from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.utils import timezone
from apps.core.fields import EncryptedTextField


class PrivateFile(BaseModel):
    owner = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    original_name = models.CharField(max_length=255)
    stored_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=120)
    size = models.PositiveIntegerField(default=0)
    sha256 = models.CharField(max_length=64)
    purpose = models.CharField(max_length=80)


class Company(BaseModel):
    company_name = models.CharField(max_length=200, blank=True, default='Example Company')
    contact_person = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)
    country = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    state = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    postal_code = models.CharField(max_length=200, blank=True)
    email = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=200, blank=True)
    mobile = models.CharField(max_length=200, blank=True)
    fax = models.CharField(max_length=200, blank=True)
    cin = models.CharField(max_length=200, blank=True)
    website_url = models.CharField(max_length=200, blank=True)
    tax_id = models.CharField(max_length=200, blank=True)
    registration_no = models.CharField(max_length=200, blank=True)
    handbook = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    logo = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    time_zone = models.CharField(max_length=200, blank=True, default='Europe/London')


class Theme(BaseModel):
    site_logo = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    favicon = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    primary_color = models.CharField(max_length=7, blank=True, default='#021156')
    secondary_color = models.CharField(max_length=7, blank=True, default='#ea0606')
    sidebar_color = models.CharField(max_length=7, blank=True, default='#0d339c')
    auto_punching = models.BooleanField(default=False)


class Localisation(BaseModel):
    country = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    date_format = models.CharField(max_length=200, blank=True, default='DD-MM-YYYY')
    timezone = models.CharField(max_length=200, blank=True, default='Europe/London')
    language = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    currency_code = models.CharField(max_length=200, blank=True, default='GBP')
    currency_symbol = models.CharField(max_length=200, blank=True, default='£')


class SmtpProfile(BaseModel):
    profile = models.CharField(max_length=60, choices=[('HR', 'HR'), ('PMO', 'PMO')], default='HR')
    host = models.CharField(max_length=200, blank=True)
    username = models.CharField(max_length=200, blank=True)
    password = EncryptedTextField(blank=True)
    port = models.PositiveIntegerField(default=587)
    from_address = models.CharField(max_length=200, blank=True)
    from_name = models.CharField(max_length=200, blank=True)
    security = models.CharField(max_length=60, choices=[('TLS', 'TLS'), ('SSL', 'SSL')], default='TLS')
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['profile'], condition=Q(is_deleted=False), name='unique_smtp_profile'),
        ]


class EmailDelivery(BaseModel):
    profile = models.CharField(max_length=10, default='HR')
    recipient = models.EmailField()
    subject = models.CharField(max_length=250)
    body = EncryptedTextField()
    delivery_status = models.CharField(max_length=20, default='Pending')
    attempts = models.PositiveIntegerField(default=0)
    error = models.CharField(max_length=100, blank=True)
