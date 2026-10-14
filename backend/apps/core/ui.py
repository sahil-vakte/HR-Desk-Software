from django.apps import apps
from django.db import models
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from .registry import RESOURCES, MASTERS
from .access import has_menu, is_hr
from .api import model_serializer, MESSAGES
from .fields import EncryptedTextField

PATHS={'leave/requests':'/leave','leave/entitlements':'/leave/entitlements','wfh-requests':'/wfh','holiday-years':'/masters/holiday-years','leave-years':'/masters/leave-years','leave-types':'/masters/leave-types','holidays':'/holidays','newsletters':'/pmo/newsletters','wsr':'/pmo/wsr','queries':'/pmo/queries','whos-where':'/pmo/whos-where','hierarchy-documents':'/employees/hierarchy','hiring-documents':'/employees/hiring-process','attendance/records':'/attendance/admin'}

class ResourceMetadata(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        output=[]
        for key,spec in RESOURCES.items():
            if not has_menu(request.user,spec.menu) and not (spec.scope=='leave' and has_menu(request.user,31)):continue
            if key=='employees' and not is_hr(request.user):continue
            model=apps.get_model(spec.model)
            serializer=model_serializer(model,request.user)()
            fields=[]
            for name,sfield in serializer.fields.items():
                if name in ['created_at','updated_at']:continue
                field=model._meta.get_field(name)
                typ='text';relation=None
                if isinstance(field,models.BooleanField):typ='boolean'
                elif isinstance(field,models.DateTimeField):typ='datetime-local'
                elif isinstance(field,models.DateField):typ='date'
                elif isinstance(field,(models.IntegerField,models.DecimalField)):typ='number'
                elif isinstance(field,models.JSONField):typ='json'
                elif isinstance(field,models.TextField):typ='richtext' if name in ['message','description','notes'] else 'textarea'
                if field.is_relation:
                    typ='file' if field.related_model._meta.label=='core.PrivateFile' else 'select'
                    relation=field.related_model._meta.label
                choices=list(getattr(field,'choices',[]) or [])
                if choices:typ='choice'
                fields.append({'name':name,'label':name.replace('_',' ').capitalize(),'type':typ,'required':sfield.required,
                    'read_only':sfield.read_only,'multiple':field.many_to_many,'relation':relation,'choices':choices,
                    'message':MESSAGES.get(model.__name__,{}).get(name),'default':field.get_default() if field.has_default() else None,
                    'sensitive':isinstance(field,EncryptedTextField)})
            if model.__name__=='MasterItem':
                slug=key.split('/')[-1]
                extra={'working-modes':['description'],'processes':['time_zone'],'document-list':['parent'],'locations':['parent'],'job-titles':['description','file'],'clients':['email','contact_no','description'],'customers':['description'],'reporting-managers':['parent','extra'],'letters':['description']}.get(slug,[])
                fields=[f for f in fields if f['name'] in ['id','name','status']+extra]
            writable=spec.scope!='readonly' and (spec.scope not in ['projects','read_all'] or is_hr(request.user))
            actions=[]
            if is_hr(request.user):
                if model.__name__ in ['LeaveRequest','WfhRequest','WeeklyStatusReport']:actions=['approve','reject']
                if model.__name__=='LeaveRequest':actions+=['approve-unpaid']
                if model.__name__=='Timesheet':actions=['accept','reject']
                if model.__name__=='Query':actions=['close']
                if any(f.name=='is_archived' for f in model._meta.fields):actions+=['archive']
            output.append({'key':key,'title':spec.title,'path':PATHS.get(key,'/'+key),'fields':fields,'writable':writable,'actions':actions})
        return Response(output)

class LookupView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,kind):
        from apps.masters.models import MasterItem
        from apps.accounts.models import User
        if kind in ['users','accounts.User']:
            return Response([{'id':u.pk,'name':u.get_full_name() or u.username} for u in User.objects.filter(is_active=True,is_deleted=False)])
        if kind in MASTERS:
            return Response(list(MasterItem.objects.filter(kind=kind,status=True).values('id','name')))
        if kind=='masters.MasterItem':
            return Response([{'id':m.pk,'name':f'{m.kind}: {m.name}'} for m in MasterItem.objects.filter(status=True)])
        if kind in ['leave.LeaveType','leave.LeaveYear'] and (has_menu(request.user,55) or has_menu(request.user,56) or has_menu(request.user,31)):
            from .services import employee_for
            model=apps.get_model(kind)
            rows=model.objects.filter(status=True)
            if not is_hr(request.user):rows=rows.filter(process=employee_for(request.user).process)
            if kind=='leave.LeaveType':rows=rows.filter(leave_year__status=True)
            return Response([{'id':r.pk,'name':r.name if hasattr(r,'name') else f'{r.from_date} – {r.to_date}'} for r in rows])
        if kind=='accounts.Role':
            from .access import require_super
            require_super(request.user)
            return Response([{'id':r.pk,'name':r.title} for r in apps.get_model('accounts.Role').objects.filter(status=True)])
        candidates=[(key,s) for key,s in RESOURCES.items() if s.model==kind]
        if not candidates:raise ValidationError({'kind':['Unknown lookup.']})
        for key,spec in candidates:
            if not has_menu(request.user,spec.menu):continue
            from .api import ResourceViewSet
            view=ResourceViewSet();view.request=request;view.resource_key=key
            rows=view.get_queryset()
            if hasattr(rows.model,'status') and isinstance(rows.model._meta.get_field('status'),models.BooleanField):rows=rows.filter(status=True)
            return Response([{'id':r.pk,'name':getattr(r,'name',None) or getattr(r,'title',None) or getattr(r,'employee_code',None) or f'{kind.split(".")[-1]} {r.pk}'} for r in rows])
        raise PermissionDenied()

class ProfileMetadata(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,section):
        from .registry import PROFILE
        if section not in PROFILE:raise ValidationError({'section':['Unknown section.']})
        if not has_menu(request.user,29) and not has_menu(request.user,71):raise PermissionDenied()
        model=apps.get_model('employees',PROFILE[section])
        serializer=model_serializer(model,request.user)()
        fields=[]
        for name,sfield in serializer.fields.items():
            if name in ['created_at','updated_at','user']:continue
            field=model._meta.get_field(name)
            typ='text';relation=None
            if isinstance(field,models.BooleanField):typ='boolean'
            elif isinstance(field,models.DateField):typ='date'
            elif isinstance(field,(models.IntegerField,models.DecimalField)):typ='number'
            elif isinstance(field,models.JSONField):typ='json'
            elif isinstance(field,models.TextField):typ='textarea'
            if field.is_relation:
                typ='file' if field.related_model._meta.label=='core.PrivateFile' else 'select';relation=field.related_model._meta.label
            choices=list(getattr(field,'choices',[]) or [])
            if choices:typ='choice'
            fields.append({'name':name,'label':name.replace('_',' ').capitalize(),'type':typ,'required':sfield.required,'read_only':sfield.read_only,'multiple':False,'relation':relation,'choices':choices,'default':field.get_default() if field.has_default() else None})
        return Response({'key':section,'title':section.replace('-',' '),'fields':fields})
