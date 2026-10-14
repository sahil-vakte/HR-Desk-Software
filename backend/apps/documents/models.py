from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.utils import timezone
from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class Policy(BaseModel):
    code = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    version = models.CharField(max_length=200)
    effective_from = models.DateField()
    last_update = models.DateField()
    sub_units = models.ManyToManyField('masters.MasterItem', blank=True, related_name="+")
    url = models.CharField(max_length=500, blank=True)
    attachment = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    description = models.TextField(blank=True)


class HoDocument(BaseModel):
    name = models.CharField(max_length=200)
    uploaded_date = models.DateField()
    description = models.TextField(blank=True)
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    is_archived = models.BooleanField(default=False)
