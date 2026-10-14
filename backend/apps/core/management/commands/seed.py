import json
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify
from apps.accounts.models import Role, MenuItem, RolePermission
from apps.masters.models import MasterItem, WorkWeek
from apps.core.models import Company, Theme, Localisation
from apps.core.registry import RESOURCES, MASTERS

class Command(BaseCommand):
    help='Seed authoritative role grants and reference master lists idempotently.'
    def add_arguments(self,parser):parser.add_argument('--check',action='store_true')
    @transaction.atomic
    def handle(self,*args,**options):
        root=Path(settings.BASE_DIR).parent/'specification'/'schemas'
        permission=json.loads((root/'permissions.json').read_text())
        seed=json.loads((root/'seed-data.json').read_text())
        ids=[x['menu_id'] for x in permission['menu_items']]
        if len(ids)!=75 or len(set(ids))!=75:raise CommandError('Expected 75 unique menu permissions.')
        if options['check']:
            self.stdout.write('Validated 75 unique menu permissions.');return
        menu_routes={1:'/',46:'/leave/manager',71:'/me/profile',29:'/employees',28:'/attendance/admin',31:'/leave/admin',81:'/employees/hiring-process',75:'/employees/hierarchy',16:'/holidays',55:'/leave',56:'/leave/balance',27:'/attendance',30:'/policies',58:'/directory',65:'/projects',66:'/tasks',77:'/pmo/newsletters',78:'/pmo/wsr',79:'/pmo/queries',80:'/pmo/whos-where',82:'/timesheets',42:'/reports/leave',68:'/reports/attendance',85:'/reports/pmo',40:'/settings/company',36:'/settings/email',34:'/settings/theme',35:'/settings/localisation',52:'/wfh',45:'/rms/roles',47:'/rms/applicants',69:'/rms/documents',86:'/rms/pipeline',57:'/masters/leave-years',84:'/masters/holiday-years',83:'/ho-documents',54:'/masters/technical-questions',53:'/masters/interview-questions',15:'/masters/work-week'}
        for slug,(code,title) in MASTERS.items():menu_routes.setdefault(code,'/masters/'+slug)
        for index,item in enumerate(permission['menu_items']):
            row=MenuItem.all_objects.filter(pk=item['menu_id']).first() or MenuItem(pk=item['menu_id'])
            row.title=item['label'];row.slug=slugify(item['label']);row.route=menu_routes.get(row.pk,'')
            row.order=index;row.is_menu=row.pk not in [9,37,38,59];row.master_status=True
            row.save()
        for item in permission['menu_items']:
            row=MenuItem.objects.get(pk=item['menu_id']);row.parent_id=item['parent_id'];row.save()
        for code,source in permission['roles'].items():
            role=Role.all_objects.filter(pk=int(code)).first() or Role(pk=int(code))
            role.title=source['name'];role.slug=slugify(source['name']);role.save()
            # Initial seed never overwrites administrator-edited grants on subsequent runs.
            if not RolePermission.all_objects.filter(role=role).exists():
                for menu_id in source['permissions']:RolePermission(role=role,menu_item_id=menu_id).save()
        mapping={'education_levels':'education-levels','employment_statuses':'employment-statuses','working_modes':'working-modes','document_types':'document-types','document_list':'document-list','sub_units':'sub-units','job_titles':'job-titles','termination_reasons':'termination-reasons','work_authorizations':'work-authorizations','currency_codes':'currency-codes','technical_statuses':'technical-statuses','interview_statuses':'interview-statuses','evaluation_statuses':'evaluation-statuses'}
        for key,source in seed['lists'].items():
            kind=mapping.get(key,key.replace('_','-'))
            if kind not in MASTERS:continue
            for source_row in source.get('rows',[]):
                name=source_row.get('Name',source_row.get('Title',source_row.get('Country','')))
                if not name:continue
                if not MasterItem.all_objects.filter(kind=kind,name__iexact=name).exists():
                    MasterItem(kind=kind,name=name,status=source_row.get('Status','Active')=='Active',description=source_row.get('Description',''),time_zone=source_row.get('TimeZone','Europe/London')).save()
        process=MasterItem.objects.filter(kind='processes',name='UK').first()
        if process and not WorkWeek.objects.filter(process=process).exists():WorkWeek(process=process).save()
        for model in [Company,Theme,Localisation]:
            if not model.objects.exists():model().save()
        self.stdout.write(self.style.SUCCESS('Seeded roles, 75 menu permissions and captured reference lists.'))
