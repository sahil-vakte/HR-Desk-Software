from django.db import models
from django.db.models import Q, F
from django.db.models.functions import Lower
from django.utils import timezone
from apps.core.fields import EncryptedTextField
from apps.core.models import BaseModel


class JobRole(BaseModel):
    reference_no = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    positions = models.PositiveIntegerField(default=1)
    publish_date = models.DateField()
    expiry_date = models.DateField()
    portal1_name = models.CharField(max_length=200, blank=True)
    portal1_reference = models.CharField(max_length=200, blank=True)
    portal2_name = models.CharField(max_length=200, blank=True)
    portal2_reference = models.CharField(max_length=200, blank=True)
    portal3_name = models.CharField(max_length=200, blank=True)
    portal3_reference = models.CharField(max_length=200, blank=True)
    salary_min_gbp = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    salary_max_gbp = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    description = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    status = models.CharField(max_length=60, choices=[('Open', 'Open'), ('Paused', 'Paused'), ('Closed', 'Closed')], default='Open')
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['reference_no'], condition=Q(is_deleted=False), name='unique_job_reference'),
            models.CheckConstraint(condition=Q(salary_max_gbp__gte=F("salary_min_gbp")), name='salary_range'),
        ]


class Applicant(BaseModel):
    job_role = models.ForeignKey('recruitment.JobRole', on_delete=models.PROTECT, related_name="+")
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=200, blank=True)
    cv_file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    cv_text = models.TextField(blank=True)
    application_date = models.DateField()
    respond_to_portal = models.CharField(max_length=200, blank=True)
    work_authorization = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    cv_evaluation_date = models.DateField(null=True, blank=True)
    technical_test_date = models.DateField(null=True, blank=True)
    final_interview_date = models.DateField(null=True, blank=True)
    cif_date = models.DateField(null=True, blank=True)
    job_offered_date = models.DateField(null=True, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    cv_evaluation_status = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    technical_test_status = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    final_interview_status = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    application_pack_location = models.CharField(max_length=200, blank=True)
    applicant_status = models.CharField(max_length=60, choices=[('Awaiting', 'Awaiting'), ('Selected', 'Selected'), ('Joined', 'Joined'), ('Rejected', 'Rejected')], default='Awaiting')


class CvEvaluation(BaseModel):
    applicant = models.ForeignKey('recruitment.Applicant', on_delete=models.PROTECT, related_name="+")
    assessor_name = models.CharField(max_length=200)
    assessment_date = models.DateField()
    ratings = models.JSONField(default=list)
    outcome = models.CharField(max_length=60, choices=[('Strong', 'Strong'), ('Potential', 'Potential'), ('Rejected', 'Rejected')], default='Strong')
    note = models.TextField(blank=True)
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['applicant'], condition=Q(is_deleted=False), name='unique_cv_evaluation'),
        ]


class TechnicalQuestion(BaseModel):
    job_roles = models.ManyToManyField('recruitment.JobRole', blank=True, related_name="+")
    type = models.CharField(max_length=60, choices=[('MCQ', 'MCQ'), ('Brief', 'Brief')], default='MCQ')
    question = models.TextField(blank=True)
    option_a = models.CharField(max_length=500, blank=True)
    option_b = models.CharField(max_length=500, blank=True)
    option_c = models.CharField(max_length=500, blank=True)
    option_d = models.CharField(max_length=500, blank=True)
    correct_answer = models.CharField(max_length=500, blank=True)
    code_snippet = models.TextField(blank=True)
    answer_explanation = models.TextField(blank=True)
    video_link = models.CharField(max_length=500, blank=True)
    image = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")


class InterviewQuestion(BaseModel):
    job_roles = models.ManyToManyField('recruitment.JobRole', blank=True, related_name="+")
    type = models.CharField(max_length=60, choices=[('Panel 1', 'Panel 1'), ('Panel 2', 'Panel 2'), ('Panel 3', 'Panel 3')], default='Panel 1')
    question = models.TextField(blank=True)


class InterviewNote(BaseModel):
    applicant = models.ForeignKey('recruitment.Applicant', on_delete=models.PROTECT, related_name="+")
    panel = models.PositiveIntegerField(default=1)
    interviewer = models.ForeignKey('accounts.User', on_delete=models.PROTECT, related_name="+")
    date = models.DateField()
    notes = models.TextField(blank=True)
    outcome = models.ForeignKey('masters.MasterItem', on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['applicant', 'panel'], condition=Q(is_deleted=False), name='unique_interview_panel'),
        ]


class ApplicantDocument(BaseModel):
    applicant = models.ForeignKey('recruitment.Applicant', on_delete=models.PROTECT, related_name="+")
    name = models.CharField(max_length=200)
    file = models.ForeignKey("core.PrivateFile", null=True, blank=True, on_delete=models.PROTECT, related_name="+")


class CandidateInvitation(BaseModel):
    applicant = models.ForeignKey('recruitment.Applicant', on_delete=models.PROTECT, related_name="+")
    kind = models.CharField(max_length=60, choices=[('test', 'test'), ('cif', 'cif'), ('reference', 'reference')], default='test')
    digest = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)
    questions = models.JSONField(default=dict, blank=True)
    answers = EncryptedTextField(blank=True)
    class Meta(BaseModel.Meta):
        constraints = BaseModel.Meta.constraints + [
            models.UniqueConstraint(fields=['digest'], condition=Q(is_deleted=False), name='unique_invitation'),
        ]
