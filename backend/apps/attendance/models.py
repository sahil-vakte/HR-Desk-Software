from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.utils import timezone
from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class AttendanceSession(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    date = models.DateField()
    work_mode = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    punch_in = models.DateTimeField()
    punch_out = models.DateTimeField(null=True, blank=True)
    total_minutes = models.PositiveIntegerField(default=0)
    source = models.CharField(max_length=60, choices=[('self', 'self'), ('admin', 'admin')], default='self')
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=["user"], condition=Q(punch_out__isnull=True, is_deleted=False), name="one_open_punch"),
            models.CheckConstraint(condition=Q(punch_out__isnull=True)|Q(punch_out__gt=F("punch_in")), name='punch_time_order'),
        ]


class PunchSetting(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    working_capacity_pct = models.PositiveIntegerField(default=100)
    hours_per_week = models.DecimalField(max_digits=12, decimal_places=2, default=40)
    mon = models.BooleanField(default=True)
    tue = models.BooleanField(default=True)
    wed = models.BooleanField(default=True)
    thu = models.BooleanField(default=True)
    fri = models.BooleanField(default=True)
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['user'], condition=Q(is_deleted=False), name='unique_punch_settings'),
        ]
