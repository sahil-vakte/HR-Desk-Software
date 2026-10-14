from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.utils import timezone
from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class WfhRequest(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    duration = models.CharField(max_length=60, choices=[('Full Day', 'Full Day'), ('First Half', 'First Half'), ('Second Half', 'Second Half')], default='Full Day')
    date = models.DateField()
    comment = models.TextField(blank=True)
    status = models.CharField(max_length=60, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Rejected', 'Rejected')], default='Pending')
    rejection_reason = models.TextField(blank=True)
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['user', 'date'], condition=Q(is_deleted=False), name='unique_wfh_day'),
        ]
