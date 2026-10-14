from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.utils import timezone
from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class Project(BaseModel):
    name = models.CharField(max_length=200)
    client = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    lead = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    members = models.ManyToManyField('accounts.User', blank=True, related_name="+")
    description = models.TextField(blank=True)
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.CheckConstraint(condition=Q(end_date__isnull=True)|Q(end_date__gte=F("start_date")), name='project_dates'),
        ]


class ProjectDocument(BaseModel):
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, related_name="+")
    name = models.CharField(max_length=200)
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")


class Task(BaseModel):
    project = models.ForeignKey('projects.Project', on_delete=models.PROTECT, related_name="+")
    name = models.CharField(max_length=200)
    priority = models.CharField(max_length=60, choices=[('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], default='High')
    assignees = models.ManyToManyField('accounts.User', blank=True, related_name="+")
    deadline = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=60, choices=[('To Do', 'To Do'), ('Not Started', 'Not Started'), ('In progress', 'In progress'), ('Testing', 'Testing'), ('On Hold', 'On Hold'), ('Review', 'Review'), ('Completed', 'Completed')], default='To Do')
    total_hours = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estimated_hours = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    remaining_hours = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)


class TaskComment(BaseModel):
    task = models.ForeignKey('projects.Task', on_delete=models.PROTECT, related_name="+")
    author = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    message = models.TextField(blank=True)
    attachment = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
