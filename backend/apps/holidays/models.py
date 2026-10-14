from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.utils import timezone
from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class HolidayYear(BaseModel):
    from_date = models.DateField()
    to_date = models.DateField()
    is_default = models.BooleanField(default=False)
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.CheckConstraint(condition=Q(from_date__lt=F("to_date")), name='holiday_year_dates'),
        ]


class Holiday(BaseModel):
    holiday_year = models.ForeignKey('holidays.HolidayYear', on_delete=models.PROTECT, related_name="+")
    name = models.CharField(max_length=200)
    date = models.DateField()
    type = models.CharField(max_length=60, choices=[('Full Day', 'Full Day'), ('Half Day', 'Half Day')], default='Full Day')
    process = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['holiday_year', 'date', 'process'], condition=Q(is_deleted=False), name='unique_holiday_date'),
        ]
