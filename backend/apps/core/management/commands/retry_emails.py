from django.core.management.base import BaseCommand
from apps.core.models import EmailDelivery
from apps.core.mail import deliver
class Command(BaseCommand):
    help='Retry failed email deliveries with fewer than three attempts.'
    def handle(self,*args,**options):
        count=0
        for row in EmailDelivery.objects.filter(delivery_status='Failed',attempts__lt=3):
            deliver(row);count+=1
        self.stdout.write(f'Processed {count} failed email deliveries.')
