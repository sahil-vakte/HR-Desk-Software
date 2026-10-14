import getpass
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from apps.accounts.models import User, Role
from apps.core.models import AuditEvent

class Command(BaseCommand):
    help='Create an administrator interactively after running seed.'
    @transaction.atomic
    def handle(self,*args,**options):
        if not Role.objects.filter(pk=1).exists():raise CommandError('Run seed first.')
        email=input('Administrator email: ').strip().lower();validate_email(email)
        if User.objects.filter(email__iexact=email).exists():raise CommandError('An account already exists for this email.')
        first=input('First name: ').strip();last=input('Last name: ').strip()
        password=getpass.getpass('Password: ');confirm=getpass.getpass('Confirm password: ')
        if password!=confirm:raise CommandError('Passwords do not match.')
        validate_password(password)
        user=User(username=email,email=email,first_name=first,last_name=last,role_id=1,is_staff=True)
        user.set_password(password);user.save()
        AuditEvent.objects.create(actor=user,entity='accounts.user',entity_id=str(user.pk),action='administrator_created')
        self.stdout.write(self.style.SUCCESS('Administrator created.'))
