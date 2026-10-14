from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.utils import timezone
from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class WeeklyStatusReport(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    week_start = models.DateField()
    week_end = models.DateField()
    submitted_by = models.CharField(max_length=60, choices=[('Employee', 'Employee'), ('Admin', 'Admin')], default='Employee')
    attachment = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=60, choices=[('Submitted', 'Submitted'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Submitted')
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['user', 'week_start'], condition=Q(is_deleted=False), name='unique_wsr'),
        ]


class Query(BaseModel):
    query_code = models.CharField(max_length=200)
    employee = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    created_by = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    subject = models.CharField(max_length=200)
    priority = models.CharField(max_length=60, choices=[('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], default='High')
    message = models.TextField(blank=True)
    attachment = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=60, choices=[('In-Progress', 'In-Progress'), ('Closed', 'Closed')], default='In-Progress')
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['query_code'], condition=Q(is_deleted=False), name='unique_query_code'),
        ]


class QueryReply(BaseModel):
    query = models.ForeignKey('pmo.Query', on_delete=models.PROTECT, related_name="+")
    author = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    message = models.TextField(blank=True)
    attachment = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")


class WhosWhereEntry(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    week_start = models.DateField()
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    day1 = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    day2 = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    day3 = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    day4 = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    day5 = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['user', 'week_start'], condition=Q(is_deleted=False), name='unique_whos_where'),
        ]
