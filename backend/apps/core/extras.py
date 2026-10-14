from datetime import date, timedelta
from pathlib import Path
import json
from django.apps import apps
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import EmailMessage
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from .access import require_menu, require_super, require_hr, is_hr
from .api import model_serializer
from .models import AuditEvent, Company, Theme, PrivateFile
from .services import employee_for, leave_usage, work_capacity
from apps.accounts.models import User
from apps.employees.models import Employee, OrgDocument
from apps.projects.models import Project, ProjectDocument, Task, TaskComment
from apps.pmo.models import WhosWhereEntry
from apps.masters.models import MasterItem
from apps.leave.models import LeaveRequest
from apps.wfh.models import WfhRequest
from apps.reports.views import export_rows

class Branding(APIView):
    permission_classes=[AllowAny]
    authentication_classes=[]
    def get(self,request):
        company=Company.objects.first();theme=Theme.objects.first()
        return Response({'company_name':company.company_name if company else 'HRDESK',
            'primary_color':theme.primary_color if theme else '#021156','secondary_color':theme.secondary_color if theme else '#ea0606','sidebar_color':theme.sidebar_color if theme else '#0d339c'})

class AuditList(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        require_super(request.user)
        qs=AuditEvent.objects.order_by('-at')
        for name in ['entity','entity_id']:
            if request.query_params.get(name):qs=qs.filter(**{name:request.query_params[name]})
        from .pagination import StandardPagination
        paginator=StandardPagination();rows=paginator.paginate_queryset(qs,request)
        return paginator.get_paginated_response([{'id':r.pk,'actor':r.actor_id,'entity':r.entity,'entity_id':r.entity_id,'action':r.action,'before':r.before,'after':r.after,'at':r.at} for r in rows])

class ProjectChildren(APIView):
    permission_classes=[IsAuthenticated]
    def parent(self,request,pk,kind):
        require_menu(request.user,65 if kind=='documents' else 66)
        project=get_object_or_404(Project.objects,pk=pk) if kind=='documents' else get_object_or_404(Task.objects,pk=pk).project
        if not is_hr(request.user) and not project.members.filter(pk=request.user.pk).exists():raise PermissionDenied()
        return project
    def get(self,request,pk,kind):
        project=self.parent(request,pk,kind)
        model=ProjectDocument if kind=='documents' else TaskComment
        qs=model.objects.filter(**({'project':project} if kind=='documents' else {'task_id':pk}))
        return Response(model_serializer(model,request.user)(qs,many=True).data)
    @transaction.atomic
    def post(self,request,pk,kind):
        project=self.parent(request,pk,kind)
        model=ProjectDocument if kind=='documents' else TaskComment
        data=request.data.copy()
        data.update({'project':project.pk} if kind=='documents' else {'task':pk,'author':request.user.pk})
        serializer=model_serializer(model,request.user)(data=data);serializer.is_valid(raise_exception=True)
        row=model(**serializer.validated_data);row.save(actor=request.user)
        return Response(model_serializer(model,request.user)(row).data,status=201)

class WhosWhere(APIView):
    permission_classes=[IsAuthenticated]
    def week(self,request):
        require_menu(request.user,80)
        try:start=date.fromisoformat(request.query_params.get('week_start',str(timezone.localdate()-timedelta(days=timezone.localdate().weekday()))))
        except ValueError:raise ValidationError({'week_start':['Invalid week.']})
        if start.weekday()!=0:raise ValidationError({'week_start':['Please select a Monday.']})
        return start
    def get(self,request):
        start=self.week(request);rows=[]
        for e in Employee.objects.filter(status=True).select_related('user','job_title'):
            stored=WhosWhereEntry.objects.filter(user=e.user,week_start=start).first()
            values={'id':e.user_id,'user':e.user_id,'employee_code':e.employee_code,'name':e.user.get_full_name(),'job_title':e.job_title.name if e.job_title else '', 'project':stored.project_id if stored else None}
            for i in range(1,6):
                current=start+timedelta(days=i-1)
                if stored:mode=getattr(stored,f'day{i}_id')
                else:
                    label='Leave' if LeaveRequest.objects.filter(user=e.user,from_date__lte=current,to_date__gte=current,status__in=['Approve With Pay','Approve Without Pay']).exists() else 'WFH' if WfhRequest.objects.filter(user=e.user,date=current,status='Approved').exists() else None
                    item=MasterItem.objects.filter(kind='working-modes',name=label,status=True).first() if label else None
                    mode=item.pk if item else e.work_mode_id
                values[f'day{i}']=mode
            rows.append(values)
        if request.query_params.get('export'):return export_rows(rows,'Whos Where',request.query_params['export'])
        return Response({'week_start':start,'rows':rows})
    @transaction.atomic
    def put(self,request):
        start=self.week(request);require_hr(request.user)
        rows=request.data.get('rows')
        if not isinstance(rows,list):raise ValidationError({'rows':['Rows are required.']})
        for data in rows:
            user=get_object_or_404(User,pk=data.get('user'),is_active=True,is_deleted=False)
            item=WhosWhereEntry.objects.filter(user=user,week_start=start).first() or WhosWhereEntry(user=user,week_start=start)
            project=Project.objects.filter(pk=data.get('project')).first() if data.get('project') else None
            if project and not project.members.filter(pk=user.pk).exists():raise ValidationError({'project':['Employee must be a project member.']})
            item.project=project
            for i in range(1,6):
                code=data.get(f'day{i}')
                mode=get_object_or_404(MasterItem.objects,pk=code,kind='working-modes',status=True) if code else None
                setattr(item,f'day{i}',mode)
            item.save(actor=request.user)
        return self.get(request)

class NewsletterSend(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,pk):
        require_menu(request.user,77);require_hr(request.user)
        item=get_object_or_404(OrgDocument.objects,pk=pk,kind='newsletter',is_archived=False)
        subject=str(request.data.get('subject','')).strip();body=str(request.data.get('message','')).strip()
        if not subject or not body:raise ValidationError({'message':['Subject and message are required.']})
        ids=request.data.get('recipients',[])
        users=list(User.objects.filter(pk__in=ids,is_active=True,is_deleted=False))
        if not users or len(users)!=len(set(ids)):raise ValidationError({'recipients':['Select valid recipients.']})
        for user in users:
            email=EmailMessage(subject,body,settings.DEFAULT_FROM_EMAIL,[user.email])
            if item.file_id:email.attach_file(Path(settings.MEDIA_ROOT)/item.file.stored_name)
            email.send(fail_silently=False)
        AuditEvent.objects.create(actor=request.user,entity='employees.orgdocument',entity_id=str(pk),action='newsletter_sent',after={'recipient_count':len(users)})
        return Response({'message':'Newsletter sent.','recipient_count':len(users)})

class AttendanceGrid(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        import calendar
        from apps.attendance.models import AttendanceSession
        require_menu(request.user,28);require_hr(request.user)
        try:
            month=int(request.query_params.get('month',timezone.localdate().month));year=int(request.query_params.get('year',timezone.localdate().year));day_count=calendar.monthrange(year,month)[1]
        except (ValueError,OverflowError):raise ValidationError({'month':['Enter a valid month and year.']})
        rows=[]
        for e in Employee.objects.filter(status=True).select_related('user'):
            sessions=AttendanceSession.objects.filter(user=e.user,date__month=month,date__year=year)
            row={'id':e.pk,'name':e.user.get_full_name(),'employee_code':e.employee_code}
            for day in range(1,day_count+1):row[str(day)]=round(sum(s.total_minutes for s in sessions if s.date.day==day)/60,2)
            row['Total Days']=sum(row[str(d)]>0 for d in range(1,day_count+1))
            row['HR']=float(sum(work_capacity(e,date(year,month,d)) for d in range(1,day_count+1))*e.weekly_work_hours/Decimal(max(1,len(e.working_days))))
            row['Taken']=float(sum(r.days for r in LeaveRequest.objects.filter(user=e.user,status='Approve With Pay',from_date__month=month,from_date__year=year)))
            row['Balance']=float(sum(leave_usage(e.user,t.leave_type)['balance'] for t in apps.get_model('leave.LeaveEntitlement').objects.filter(user=e.user)))
            rows.append(row)
        if request.query_params.get('export'):return export_rows(rows,'Attendance grid',request.query_params['export'])
        return Response({'count':len(rows),'next':None,'previous':None,'results':rows})
from decimal import Decimal

class LeaveDetailsExport(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,extension):
        require_menu(request.user,56,31)
        user=request.user
        if is_hr(user) and request.query_params.get('employee'):user=get_object_or_404(User,pk=request.query_params['employee'])
        rows=[{'Leave type':e.leave_type.name,**leave_usage(user,e.leave_type)} for e in apps.get_model('leave.LeaveEntitlement').objects.filter(user=user)]
        return export_rows(rows,'Leave details',extension)

class HolidayYearCopy(APIView):
    permission_classes=[IsAuthenticated]
    @transaction.atomic
    def post(self,request,pk):
        from apps.leave.models import LeaveYear, LeaveType
        require_menu(request.user,57)
        old=get_object_or_404(LeaveYear.objects,pk=pk)
        try:start=date.fromisoformat(request.data['from_date']);end=date.fromisoformat(request.data['to_date'])
        except (KeyError,ValueError):raise ValidationError({'dates':['Provide valid from and to dates.']})
        if start>=end:raise ValidationError({'to_date':['End date must be after start date.']})
        row=LeaveYear(from_date=start,to_date=end,process=old.process);row.save(actor=request.user)
        for original in LeaveType.objects.filter(leave_year=old):
            item=LeaveType(leave_year=row,process=old.process,name=original.name,allocation_per_year=original.allocation_per_year,status=original.status);item.save(actor=request.user)
            from .services import allocate_entitlements
            allocate_entitlements(item,request.user)
        return Response(model_serializer(LeaveYear,request.user)(row).data,status=201)
