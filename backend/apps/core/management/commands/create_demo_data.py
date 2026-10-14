import getpass
from datetime import date, timedelta
from decimal import Decimal
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from apps.accounts.models import User, Role
from apps.employees.models import Employee
from apps.masters.models import MasterItem
from apps.projects.models import Project
from apps.leave.models import LeaveYear, LeaveType
from apps.holidays.models import HolidayYear
from apps.core.services import allocate_entitlements
from apps.core.models import AuditEvent

class Command(BaseCommand):
    help='Create fictional demo users and starter configuration. Prompts for a password; never embeds one.'
    def add_arguments(self,parser):parser.add_argument('--password-env',help='Read the demo password from this environment variable for automated testing.')
    @transaction.atomic
    def handle(self,*args,**options):
        import os
        password=os.environ.get(options['password_env'],'') if options['password_env'] else getpass.getpass('Password for fictional demo accounts: ')
        validate_password(password)
        call_command('seed')
        process=MasterItem.objects.get(kind='processes',name='UK')
        workmode=MasterItem.objects.filter(kind='working-modes',name='WFO').first()
        accounts=[]
        for index,(first,last,email,role_id) in enumerate([
            ('Demo','Administrator','admin@example.invalid',1),('Alex','Example','alex@example.invalid',4),('Casey','Sample','casey@example.invalid',4)],1):
            user=User.objects.filter(email=email).first()
            if not user:
                user=User(username=email,email=email,first_name=first,last_name=last,role_id=role_id)
                user.set_password(password);user.save()
                AuditEvent.objects.create(actor=user,entity='accounts.user',entity_id=str(user.pk),action='demo_create')
            employee=Employee.objects.filter(user=user).first()
            if not employee:
                employee=Employee(user=user,employee_code=f'KN{index:03d}',date_of_joining=date(date.today().year,1,1),process=process,work_mode=workmode)
                employee.save(actor=accounts[0] if accounts else user)
            accounts.append(user)
        casey=Employee.objects.get(user=accounts[2]);casey.reports_to=accounts[1];casey.save(actor=accounts[0])
        year=date.today().year
        leave_year=LeaveYear.objects.filter(from_date=date(year,1,1),process=process).first()
        if not leave_year:
            leave_year=LeaveYear(from_date=date(year,1,1),to_date=date(year,12,31),process=process,is_default=True);leave_year.save(actor=accounts[0])
        leave_type=LeaveType.objects.filter(leave_year=leave_year,name='Demo Annual Leave').first()
        if not leave_type:
            leave_type=LeaveType(leave_year=leave_year,process=process,name='Demo Annual Leave',allocation_per_year=Decimal('25'));leave_type.save(actor=accounts[0])
        allocate_entitlements(leave_type,accounts[0])
        if not HolidayYear.objects.filter(from_date=date(year,1,1)).exists():HolidayYear(from_date=date(year,1,1),to_date=date(year,12,31),is_default=True).save(actor=accounts[0])
        if not Project.objects.filter(name='Demo onboarding project').exists():
            project=Project(name='Demo onboarding project',start_date=date(year,1,1),lead=accounts[1]);project.save(actor=accounts[0]);project.members.set(accounts[1:])
            AuditEvent.objects.create(actor=accounts[0],entity='projects.project',entity_id=str(project.pk),action='membership_change',after={'members':[u.pk for u in accounts[1:]]})
        self.stdout.write(self.style.SUCCESS('Fictional demo accounts ready: admin@example.invalid, alex@example.invalid, casey@example.invalid.'))
        self.stdout.write('Demo Annual Leave uses 25 days as fictional demonstration data only. Configure your actual allocation before use.')
