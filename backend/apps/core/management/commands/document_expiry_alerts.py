from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.accounts.models import User
from apps.employees.models import EmployeeDocument
from apps.core.models import AuditEvent
from apps.core.mail import notify
class Command(BaseCommand):
    help='Send HR document-expiry alerts at 60, 30 and 7 days, once per document/threshold/date.'
    def handle(self,*args,**options):
        today=timezone.localdate();count=0
        recipients=list(User.objects.filter(role_id=1,is_active=True,is_deleted=False).values_list('email',flat=True))
        for days in [60,30,7]:
            for row in EmployeeDocument.objects.filter(expiry_date=today+timedelta(days=days),is_archived=False):
                marker=f'expiry_{days}_{today.isoformat()}'
                if AuditEvent.objects.filter(entity='employees.employeedocument',entity_id=str(row.pk),action=marker).exists():continue
                delivered=[notify(email,'HRDESK document expiry',f'Document {row.pk} expires in {days} days. Sign in to review.') for email in recipients]
                if delivered and all(item.delivery_status=='Sent' for item in delivered):
                    AuditEvent.objects.create(entity='employees.employeedocument',entity_id=str(row.pk),action=marker)
                    count+=1
        self.stdout.write(f'Sent alerts for {count} documents.')
