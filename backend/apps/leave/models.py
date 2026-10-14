from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.utils import timezone
from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class LeaveYear(BaseModel):
    from_date = models.DateField()
    to_date = models.DateField()
    process = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, related_name="+")
    is_default = models.BooleanField(default=False)
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.CheckConstraint(condition=Q(from_date__lt=F("to_date")), name='leave_year_dates'),
        ]


class LeaveType(BaseModel):
    leave_year = models.ForeignKey('leave.LeaveYear', on_delete=models.PROTECT, related_name="+")
    name = models.CharField(max_length=200)
    allocation_per_year = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    process = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, related_name="+")
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['leave_year', 'name'], condition=Q(is_deleted=False), name='unique_leave_type'),
            models.CheckConstraint(condition=Q(allocation_per_year__gte=0), name='leave_allocation_positive'),
        ]


class LeaveEntitlement(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    leave_type = models.ForeignKey('leave.LeaveType', on_delete=models.PROTECT, related_name="+")
    assigned = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['user', 'leave_type'], condition=Q(is_deleted=False), name='unique_entitlement'),
            models.CheckConstraint(condition=Q(assigned__gte=0), name='entitlement_positive'),
        ]


class LeaveRequest(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    leave_type = models.ForeignKey('leave.LeaveType', on_delete=models.PROTECT, related_name="+")
    duration = models.CharField(max_length=60, choices=[('Full Day', 'Full Day'), ('First Half', 'First Half'), ('Second Half', 'Second Half')], default='Full Day')
    from_date = models.DateField()
    to_date = models.DateField()
    days = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    comment = models.TextField(blank=True)
    manager_status = models.CharField(max_length=60, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending')
    status = models.CharField(max_length=60, choices=[('Pending', 'Pending'), ('Approve With Pay', 'Approve With Pay'), ('Approve Without Pay', 'Approve Without Pay'), ('Rejected', 'Rejected')], default='Pending')
    rejection_reason = models.TextField(blank=True)
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.CheckConstraint(condition=Q(from_date__lte=F("to_date")), name='leave_request_dates'),
            models.CheckConstraint(condition=Q(days__gt=0), name='leave_days_positive'),
        ]


class LeaveRota(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    date = models.DateField()
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['user', 'date'], condition=Q(is_deleted=False), name='unique_rota'),
        ]
