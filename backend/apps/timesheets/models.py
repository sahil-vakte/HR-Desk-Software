from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.utils import timezone
from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class Timesheet(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    start_date = models.DateField()
    end_date = models.DateField()
    approval_status = models.CharField(max_length=60, choices=[('Pending', 'Pending'), ('Accepted', 'Accepted'), ('Rejected', 'Rejected')], default='Pending')
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['user', 'start_date'], condition=Q(is_deleted=False), name='unique_timesheet_week'),
        ]


class TimesheetLine(BaseModel):
    timesheet = models.ForeignKey("timesheets.Timesheet", on_delete=models.CASCADE, related_name="lines")
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, related_name="+")
    activity = models.CharField(max_length=200)
    day1 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    day2 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    day3 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    day4 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    day5 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    day6 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    day7 = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.CheckConstraint(condition=Q(day1__gte=0, day1__lte=10), name='timesheet_day1_range'),
            models.CheckConstraint(condition=Q(day2__gte=0, day2__lte=10), name='timesheet_day2_range'),
            models.CheckConstraint(condition=Q(day3__gte=0, day3__lte=10), name='timesheet_day3_range'),
            models.CheckConstraint(condition=Q(day4__gte=0, day4__lte=10), name='timesheet_day4_range'),
            models.CheckConstraint(condition=Q(day5__gte=0, day5__lte=10), name='timesheet_day5_range'),
            models.CheckConstraint(condition=Q(day6__gte=0, day6__lte=10), name='timesheet_day6_range'),
            models.CheckConstraint(condition=Q(day7__gte=0, day7__lte=10), name='timesheet_day7_range'),
        ]


class TimesheetLog(BaseModel):
    timesheet = models.ForeignKey('timesheets.Timesheet', on_delete=models.PROTECT, related_name="+")
    action = models.CharField(max_length=200)
    comment = models.TextField(blank=True)
    actor = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    at = models.DateTimeField(default=timezone.now)
