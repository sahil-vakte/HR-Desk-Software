from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.utils import timezone
from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class MasterItem(BaseModel):
    kind = models.CharField(max_length=70)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    time_zone = models.CharField(max_length=80, blank=True, default='Europe/London')
    parent = models.ForeignKey('self', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    email = models.CharField(max_length=200, blank=True)
    contact_no = models.CharField(max_length=200, blank=True)
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    extra = models.JSONField(default=dict, blank=True)
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(Lower("name"), "kind", condition=Q(is_deleted=False), name="unique_master_kind_name"),
        ]


class WorkWeek(BaseModel):
    process = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, related_name="+")
    mon = models.CharField(max_length=60, choices=[('Full Day', 'Full Day'), ('Half Day', 'Half Day'), ('Non-Working Day', 'Non-Working Day')], default='Full Day')
    tue = models.CharField(max_length=60, choices=[('Full Day', 'Full Day'), ('Half Day', 'Half Day'), ('Non-Working Day', 'Non-Working Day')], default='Full Day')
    wed = models.CharField(max_length=60, choices=[('Full Day', 'Full Day'), ('Half Day', 'Half Day'), ('Non-Working Day', 'Non-Working Day')], default='Full Day')
    thu = models.CharField(max_length=60, choices=[('Full Day', 'Full Day'), ('Half Day', 'Half Day'), ('Non-Working Day', 'Non-Working Day')], default='Full Day')
    fri = models.CharField(max_length=60, choices=[('Full Day', 'Full Day'), ('Half Day', 'Half Day'), ('Non-Working Day', 'Non-Working Day')], default='Full Day')
    sat = models.CharField(max_length=60, choices=[('Full Day', 'Full Day'), ('Half Day', 'Half Day'), ('Non-Working Day', 'Non-Working Day')], default='Non-Working Day')
    sun = models.CharField(max_length=60, choices=[('Full Day', 'Full Day'), ('Half Day', 'Half Day'), ('Non-Working Day', 'Non-Working Day')], default='Non-Working Day')
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['process'], condition=Q(is_deleted=False), name='unique_process_week'),
        ]
