from django.core.management.base import BaseCommand
from apps.leave.models import LeaveType
from apps.core.services import allocate_entitlements
class Command(BaseCommand):
    help='Create missing pro-rated entitlements without overwriting administrator adjustments.'
    def handle(self,*args,**options):
        total=sum(allocate_entitlements(t) for t in LeaveType.objects.filter(status=True,leave_year__status=True))
        self.stdout.write(f'Created {total} entitlements.')
