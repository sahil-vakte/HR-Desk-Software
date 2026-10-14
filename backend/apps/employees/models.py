from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.utils import timezone
from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel

def default_working_days():
    return [0, 1, 2, 3, 4]


class Employee(BaseModel):
    user = models.OneToOneField('accounts.User', on_delete=models.PROTECT, related_name="+")
    employee_code = models.CharField(max_length=30)
    date_of_birth = models.DateField(null=True, blank=True)
    date_of_joining = models.DateField()
    sub_unit = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    designation = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    nationality = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    reports_to = models.ForeignKey('accounts.User', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    employment_type = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    employee_status = models.CharField(max_length=60, choices=[('Confirm Employees', 'Confirm Employees'), ('On Probation', 'On Probation'), ('On Notice Period', 'On Notice Period')], default='Confirm Employees')
    gender = models.CharField(max_length=60, choices=[('Male', 'Male'), ('Female', 'Female'), ('Other', 'Other')], default='Male')
    marital_status = models.CharField(max_length=60, choices=[('Single', 'Single'), ('Married', 'Married'), ('Other', 'Other')], default='Single')
    process = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    work_mode = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    job_title = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    working_capacity_pct = models.PositiveIntegerField(default=100)
    working_days = models.JSONField(default=default_working_days)
    weekly_work_hours = models.DecimalField(max_digits=12, decimal_places=2, default=40)
    address = EncryptedTextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    driver_licence_number = EncryptedTextField(blank=True)
    licence_expiry = models.DateField(null=True, blank=True)
    medical_condition = EncryptedTextField(blank=True)
    deactivated_on = models.DateField(null=True, blank=True)
    photo = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    rms_applicant = models.ForeignKey('recruitment.Applicant', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['employee_code'], condition=Q(is_deleted=False), name='unique_employee_code'),
            models.CheckConstraint(condition=Q(working_capacity_pct__gte=1, working_capacity_pct__lte=100), name='employee_capacity_range'),
        ]


class EmployeeDocument(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    document_list_item = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, related_name="+")
    number = EncryptedTextField(blank=True)
    issued_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField(null=True, blank=True)
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    notes = models.TextField(blank=True)
    verified = models.BooleanField(default=False)
    checked_date = models.DateField(null=True, blank=True)
    is_archived = models.BooleanField(default=False)


class Dependent(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=100)
    phone = models.CharField(max_length=200, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")


class EmergencyContact(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    kind = models.CharField(max_length=60, choices=[('primary', 'primary'), ('secondary', 'secondary'), ('next_of_kin', 'next_of_kin')], default='primary')
    name = models.CharField(max_length=150)
    relationship = models.CharField(max_length=100)
    home_phone = models.CharField(max_length=200, blank=True)
    mobile = models.CharField(max_length=200, blank=True)
    email = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")


class Address(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    street1 = models.CharField(max_length=200, blank=True)
    street2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=200, blank=True)
    state = models.CharField(max_length=200, blank=True)
    postal_code = models.CharField(max_length=200, blank=True)
    mobile = models.CharField(max_length=200, blank=True)
    work_email = models.CharField(max_length=200, blank=True)
    other_email = models.CharField(max_length=200, blank=True)
    country = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    address_type = models.CharField(max_length=60, choices=[('Current', 'Current'), ('Past', 'Past')], default='Current')
    from_month = models.PositiveIntegerField(default=1)
    from_year = models.PositiveIntegerField(default=2026)
    to_month = models.PositiveIntegerField(default=1)
    to_year = models.PositiveIntegerField(default=2026)
    added_by = models.CharField(max_length=60, choices=[('Admin', 'Admin'), ('Employee', 'Employee')], default='Admin')
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    verified = models.BooleanField(default=False)


class Education(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    institute = models.CharField(max_length=200)
    level = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, related_name="+")
    major = models.CharField(max_length=200)
    year = models.PositiveIntegerField(default=2026)
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")


class Experience(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    company = models.CharField(max_length=200)
    job_title = models.CharField(max_length=200)
    employment_type = models.CharField(max_length=60, choices=[('Full Time', 'Full Time'), ('Part Time', 'Part Time')], default='Full Time')
    location = models.CharField(max_length=200)
    current = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")


class Skill(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    skill = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, related_name="+")
    years = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    comment = models.TextField(blank=True)


class Language(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    language = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, related_name="+")
    reading = models.BooleanField(default=False)
    writing = models.BooleanField(default=False)
    speaking = models.BooleanField(default=False)
    competency = models.CharField(max_length=60, choices=[('Poor', 'Poor'), ('Basic', 'Basic'), ('Good', 'Good'), ('Mother Tongue', 'Mother Tongue')], default='Poor')
    comment = models.TextField(blank=True)


class Membership(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    membership = models.CharField(max_length=200)
    paid_by = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, blank=True, default='GBP')
    commence = models.DateField()
    renewal = models.DateField()


class ChangeOfCircumstance(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    circumstance_type = models.JSONField(default=list)
    description = models.TextField(blank=True)
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")


class PaperworkDocument(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    document_list_item = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    date = models.DateField()
    title = models.CharField(max_length=200)


class Salary(BaseModel):
    user = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    currency = models.CharField(max_length=3, blank=True, default='GBP')
    pay_frequency = models.CharField(max_length=60, choices=[('Monthly', 'Monthly'), ('Weekly', 'Weekly'), ('Annual', 'Annual')], default='Monthly')
    effective_from = models.DateField()
    bank_details = EncryptedTextField(blank=True)


class OrgDocument(BaseModel):
    kind = models.CharField(max_length=60, choices=[('hierarchy', 'hierarchy'), ('hiring_process', 'hiring_process'), ('newsletter', 'newsletter')], default='hierarchy')
    name = models.CharField(max_length=200)
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    is_archived = models.BooleanField(default=False)
