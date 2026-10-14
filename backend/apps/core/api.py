from datetime import timedelta
from decimal import Decimal
from django.apps import apps
from django.db import IntegrityError, transaction, models
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from .registry import RESOURCES
from .access import has_menu, require_menu, is_hr, allowed_user_ids
from .services import Conflict, validate_leave, decide, allocate_entitlements
from .fields import EncryptedTextField

READ_ONLY = {'id','created_at','updated_at','is_deleted','deleted_at'}
STATE_MODELS = {'LeaveRequest','WfhRequest','WeeklyStatusReport','Query'}
SERVER_FIELDS = {'LeaveRequest':['days','manager_status','rejection_reason'], 'WfhRequest':['rejection_reason'],
 'WeeklyStatusReport':['week_end','submitted_by'], 'Query':['query_code','created_by'],
 'Timesheet':['end_date','approval_status'], 'AttendanceSession':['total_minutes','source']}
MESSAGES = {'LeaveRequest':{'leave_type':'Please select leave type.','from_date':'Please select from date.','to_date':'Please select to date.'},
 'WfhRequest':{'duration':'Please select duration.','date':'Please select date.'},
 'WeeklyStatusReport':{'week_start':'Please select date.','attachment':'Please select attachment file.'},
 'Query':{'subject':'Please enter subject.','priority':'Please select priority.','message':'Please enter message.'},
 'MasterItem':{'name':'Please enter the name.'}, 'LeaveType':{'name':'Please enter the name.','allocation_per_year':'Please enter allocation/year leaves.'}}


def model_serializer(model, user):
    readonly = READ_ONLY | set(SERVER_FIELDS.get(model.__name__,[]))
    if model.__name__ in STATE_MODELS: readonly.add('status')
    fields=[f.name for f in model._meta.fields if f.name not in {'is_deleted','deleted_at'}]
    fields += [f.name for f in model._meta.many_to_many]
    if not is_hr(user):
        fields=[n for n in fields if not isinstance(model._meta.get_field(n),EncryptedTextField)]
    extras={}
    for name,message in MESSAGES.get(model.__name__,{}).items():
        extras[name]={'required':True,'allow_null':False,'error_messages':{'required':message,'blank':message,'null':message}}
    if model.__name__=='MasterItem':readonly.add('kind')
    if model.__name__=='Employee':readonly.add('user')
    if not is_hr(user):
        for f in ['user','employee','created_by','submitted_by','verified','checked_date']:
            if f in fields:readonly.add(f)
    class Serializer(serializers.ModelSerializer):
        def validate(self, attrs):
            instance=self.instance
            merged={f.name:getattr(instance,f.name) for f in model._meta.fields} if instance else {}
            merged.update(attrs)
            for name,value in attrs.items():
                if isinstance(value,str) and name in {'description','message','notes'}:
                    import bleach
                    attrs[name]=bleach.clean(value,tags=['p','br','strong','em','u','ul','ol','li','a','blockquote','code','pre'],attributes={'a':['href','title']},protocols=['http','https','mailto'],strip=True)
                if isinstance(value,models.Model):
                    if getattr(value,'is_deleted',False):raise ValidationError({name:['This record is no longer available.']})
                    if model._meta.get_field(name).related_model._meta.label=='core.PrivateFile' and value.owner_id!=user.pk and not is_hr(user):raise PermissionDenied()
            if model.__name__ in {'LeaveYear','HolidayYear'} and merged.get('from_date') and merged.get('to_date') and merged['from_date']>=merged['to_date']:
                raise ValidationError({'to_date':['End date must be after start date.']})
            if model.__name__=='LeaveType' and merged.get('allocation_per_year',0)<0:
                raise ValidationError({'allocation_per_year':['Allocation cannot be negative.']})
            if model.__name__=='Project' and merged.get('end_date') and merged['end_date']<merged['start_date']:
                raise ValidationError({'end_date':['End date must not precede start date.']})
            if model.__name__=='Task':
                project=merged.get('project')
                if not project:raise ValidationError({'project':['Please select project.']})
                if not is_hr(user) and not project.members.filter(pk=user.pk).exists():raise PermissionDenied()
                assignees=attrs.get('assignees',list(instance.assignees.all()) if instance else [])
                if any(not project.members.filter(pk=u.pk).exists() for u in assignees):raise ValidationError({'assignees':['Assignees must be project members.']})
                for n in ['estimated_hours','total_hours','remaining_hours']:
                    if merged.get(n,0)<0:raise ValidationError({n:['Hours cannot be negative.']})
            if model.__name__=='WfhRequest':
                target=attrs.get('user',instance.user if instance else user)
                if not is_hr(user) and merged.get('date') and merged['date']<timezone.localdate():raise ValidationError({'date':['Select today or a future date.']})
                duplicates=model.objects.filter(user=target,date=merged.get('date'))
                if instance:duplicates=duplicates.exclude(pk=instance.pk)
                if duplicates.exists():raise Conflict('A request already exists for this employee and date.')
            if model.__name__=='WeeklyStatusReport' and merged.get('week_start') and merged['week_start'].weekday()!=0:
                raise ValidationError({'week_start':['Please select a Monday.']})
            if model.__name__=='MasterItem':
                kind=self.context.get('kind',instance.kind if instance else '')
                qs=model.objects.filter(kind=kind,name__iexact=attrs.get('name',instance.name if instance else '').strip())
                if instance:qs=qs.exclude(pk=instance.pk)
                if qs.exists():raise Conflict('A record with this name already exists.')
            return attrs
        class Meta:
            pass
    Serializer.Meta.model=model
    Serializer.Meta.fields=fields
    Serializer.Meta.read_only_fields=list(readonly & set(fields))
    Serializer.Meta.extra_kwargs=extras
    Serializer.Meta.validators=[]
    return Serializer


class ResourceViewSet(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    resource_key=''
    http_method_names=['get','post','patch','put','delete','head','options']
    @property
    def spec(self):return RESOURCES[self.resource_key]
    def authorize(self):
        if self.spec.scope=='leave':require_menu(self.request.user,55,31,46)
        else:require_menu(self.request.user,self.spec.menu)
        if self.resource_key=='employees' or self.resource_key.startswith('attendance/'):
            if not is_hr(self.request.user):raise PermissionDenied()
        if self.request.method not in ['GET','HEAD','OPTIONS']:
            if self.spec.scope=='readonly':raise PermissionDenied()
            if self.spec.scope=='read_all' and not is_hr(self.request.user):raise PermissionDenied()
            if self.spec.scope=='projects' and not is_hr(self.request.user):raise PermissionDenied()
    def get_queryset(self):
        self.authorize()
        user=self.request.user
        model=apps.get_model(self.spec.model)
        qs=model.objects.all().order_by('-pk')
        scope=self.spec.scope
        if scope in ['self','leave']:
            ids=allowed_user_ids(user,team=scope=='leave' or self.resource_key=='wfh-requests')
            if ids is not None:
                if scope=='leave' and not has_menu(user,46):ids=[user.pk]
                qs=qs.filter(**{self.spec.owner+'_id__in':ids})
        if scope=='projects' and not is_hr(user):qs=qs.filter(members=user)
        if scope=='tasks' and not is_hr(user):qs=qs.filter(project__members=user)
        if self.resource_key.startswith('masters/') and self.spec.model=='masters.MasterItem':qs=qs.filter(kind=self.resource_key.split('/')[1])
        if self.resource_key in ['hierarchy-documents','hiring-documents','newsletters']:
            qs=qs.filter(kind={'hierarchy-documents':'hierarchy','hiring-documents':'hiring_process','newsletters':'newsletter'}[self.resource_key])
        if self.resource_key=='rms/pipeline':qs=qs.filter(applicant_status='Selected')
        if model.__name__=='Employee':
            include=self.request.query_params.get('include','current')
            if include=='current':qs=qs.filter(status=True,deactivated_on__isnull=True)
            elif include=='past':qs=qs.filter(Q(status=False)|Q(deactivated_on__isnull=False))
        search=self.request.query_params.get('search','').strip()
        if search:
            conditions=Q()
            for field in model._meta.fields:
                if isinstance(field,(models.CharField,models.TextField)) and not isinstance(field,EncryptedTextField):conditions|=Q(**{field.name+'__icontains':search})
            qs=qs.filter(conditions)
        for field in model._meta.fields:
            if field.name in self.request.query_params and field.name not in READ_ONLY:
                value=self.request.query_params[field.name]
                if value:
                    if isinstance(field,models.BooleanField):value=value.lower()=='true'
                    try:qs=qs.filter(**{field.name:value})
                    except (ValueError,TypeError):raise ValidationError({field.name:['Invalid filter value.']})
        return qs.distinct()
    def get_serializer_class(self):return model_serializer(apps.get_model(self.spec.model),self.request.user)
    def get_serializer_context(self):
        context=super().get_serializer_context()
        if self.resource_key.startswith('masters/'):context['kind']=self.resource_key.split('/')[1]
        return context
    def save_record(self,serializer,instance=None):
        self.authorize()
        model=serializer.Meta.model
        if instance and self.spec.scope in ['self','leave'] and not is_hr(self.request.user) and getattr(instance,self.spec.owner+'_id')!=self.request.user.pk:
            raise PermissionDenied()
        data=dict(serializer.validated_data)
        m2m={f.name:data.pop(f.name) for f in model._meta.many_to_many if f.name in data}
        if self.spec.scope in ['self','leave'] and not is_hr(self.request.user):data[self.spec.owner]=self.request.user
        if model.__name__=='Employee' and instance is None:raise ValidationError({'user':['Create employee via employee onboarding.']})
        if model.__name__=='MasterItem':data['kind']=self.resource_key.split('/')[1]
        if model.__name__=='OrgDocument':data['kind']={'hierarchy-documents':'hierarchy','hiring-documents':'hiring_process','newsletters':'newsletter'}[self.resource_key]
        if model.__name__=='Query' and not instance:
            data['created_by']=self.request.user
            data['query_code']='Qexample'+timezone.now().strftime('%Y%m%d%H%M%S%f')
        if model.__name__=='WeeklyStatusReport':
            data['submitted_by']='Admin' if is_hr(self.request.user) else 'Employee'
            data['week_end']=data.get('week_start',instance.week_start if instance else None)+timedelta(days=6)
        if model.__name__=='Timesheet':raise ValidationError({'non_field_errors':['Use the weekly timesheet editor.']})
        if instance and model.__name__ in STATE_MODELS:
            if getattr(instance,'status') not in ['Pending','Submitted','In-Progress']:raise Conflict('This record can no longer be edited.')
        if model.__name__=='LeaveRequest':
            merged={f.name:getattr(instance,f.name) for f in model._meta.fields} if instance else {}
            merged.update(data)
            data=validate_leave(merged,merged.get('user',self.request.user),instance)
            data={k:v for k,v in data.items() if k not in READ_ONLY}
        if instance is None:instance=model(**data)
        else:
            for k,v in data.items():setattr(instance,k,v)
        instance.full_clean(exclude=[f.name for f in model._meta.fields if f.name in READ_ONLY],validate_unique=False,validate_constraints=False)
        instance.save(actor=self.request.user)
        for key,values in m2m.items():
            before=list(getattr(instance,key).values_list('pk',flat=True))
            getattr(instance,key).set(values)
            from .models import AuditEvent
            AuditEvent.objects.create(actor=self.request.user,entity=instance._meta.label_lower,entity_id=str(instance.pk),action='membership_change',before={key:before},after={key:[v.pk for v in values]})
        if model.__name__=='Query' and not serializer.instance:
            instance.query_code=f'Qexample{instance.pk:02d}'
            instance.save(actor=self.request.user)
        if model.__name__=='LeaveType' and instance.status:allocate_entitlements(instance,self.request.user)
        serializer.instance=instance
        if model.__name__ in ['LeaveRequest','WfhRequest','Query']:
            from .mail import request_notification
            transaction.on_commit(lambda: request_notification(instance))
    def perform_create(self,serializer):
        try:
            with transaction.atomic():self.save_record(serializer)
        except IntegrityError:raise Conflict()
    def perform_update(self,serializer):
        try:
            with transaction.atomic():self.save_record(serializer,serializer.instance)
        except IntegrityError:raise Conflict()
    def perform_destroy(self,instance):
        self.authorize()
        if self.spec.scope in ['self','leave'] and not is_hr(self.request.user):
            if getattr(instance,self.spec.owner+'_id')!=self.request.user.pk or getattr(instance,'status','Pending')!='Pending':raise PermissionDenied()
        if self.resource_key=='employees':raise ValidationError({'non_field_errors':['Deactivate the employee account through employee onboarding.']})
        instance.delete(actor=self.request.user)
    @action(detail=True,methods=['post'],url_path='(?P<decision>approve|approve-unpaid|reject|accept|close)')
    def decision(self,request,pk=None,decision=None):
        row=decide(self.get_object(),decision,request.user,request.data.get('reason',request.data.get('comment','')))
        return Response(self.get_serializer(row).data)
    @action(detail=False,methods=['get'])
    def manage(self,request):
        if not is_hr(request.user):raise PermissionDenied()
        return self.list(request)
    @action(detail=False,methods=['get'])
    def team(self,request):
        require_menu(request.user,46)
        from apps.core.access import reporting_manager
        if not reporting_manager(request.user):raise PermissionDenied()
        return self.list(request)
    @action(detail=True,methods=['get'],url_path='assignable-users')
    def assignable_users(self,request,pk=None):
        if self.resource_key!='projects':raise PermissionDenied()
        require_menu(request.user,66)
        return Response([{'id':u.pk,'name':u.get_full_name()} for u in self.get_object().members.filter(is_active=True,is_deleted=False)])
    @action(detail=True,methods=['post'])
    def archive(self,request,pk=None):
        instance=self.get_object()
        if not hasattr(instance,'is_archived') or not is_hr(request.user):raise PermissionDenied()
        instance.is_archived=True
        instance.save(actor=request.user)
        return Response(self.get_serializer(instance).data)
