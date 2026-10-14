from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.accounts.models import User
from apps.core.access import require_menu, is_hr
from apps.core.services import employee_for, work_capacity, Conflict
from apps.core.api import model_serializer
from apps.projects.models import Project
from apps.leave.models import LeaveRequest
from .models import Timesheet, TimesheetLine, TimesheetLog

class WeekView(APIView):
    permission_classes=[IsAuthenticated]
    def context(self,request,user_id,week_start):
        require_menu(request.user,82)
        user_id=int(user_id)
        if request.user.pk!=user_id and not is_hr(request.user):raise PermissionDenied()
        user=get_object_or_404(User,is_active=True,is_deleted=False,pk=user_id)
        try:start=date.fromisoformat(week_start)
        except ValueError:raise ValidationError({'start_date':['Invalid date.']})
        if start.weekday()!=0:raise ValidationError({'start_date':['Please select a Monday.']})
        return user,start
    def payload(self,request,user,start):
        employee=employee_for(user)
        row=Timesheet.objects.filter(user=user,start_date=start).first()
        days=[]
        for i in range(7):
            current=start+timedelta(days=i)
            full_leave=LeaveRequest.objects.filter(user=user,from_date__lte=current,to_date__gte=current,status__in=['Approve With Pay','Approve Without Pay'],duration='Full Day').exists()
            days.append({'date':str(current),'disabled':work_capacity(employee,current)==0 or full_leave})
        return {'id':row.pk if row else None,'user':user.pk,'start_date':str(start),'end_date':str(start+timedelta(days=6)),
            'approval_status':row.approval_status if row else 'Pending','days':days,
            'lines':model_serializer(TimesheetLine,request.user)(row.lines.filter(is_deleted=False),many=True).data if row else []}
    def get(self,request,user_id,week_start):
        user,start=self.context(request,user_id,week_start)
        return Response(self.payload(request,user,start))
    @transaction.atomic
    def put(self,request,user_id,week_start):
        user,start=self.context(request,user_id,week_start)
        row=Timesheet.objects.select_for_update().filter(user=user,start_date=start).first()
        if row and row.approval_status=='Accepted':raise Conflict('An accepted timesheet cannot be edited.')
        lines=request.data.get('lines')
        if not isinstance(lines,list) or not lines:raise ValidationError({'lines':['Add at least one timesheet line.']})
        if len(lines)>100:raise ValidationError({'lines':['A timesheet may contain at most 100 lines.']})
        days=self.payload(request,user,start)['days']
        cleaned=[]
        for index,line in enumerate(lines):
            if not isinstance(line,dict):raise ValidationError({'lines':['Invalid line.']})
            project=Project.objects.filter(pk=line.get('project'),status=True).first()
            if not project:raise ValidationError({'lines':[f'Line {index+1}: Project is required.']})
            if not project.members.filter(pk=user.pk).exists():raise ValidationError({'lines':['Select a project assigned to the employee.']})
            if not str(line.get('activity','')).strip():raise ValidationError({'lines':['Activity is required.']})
            values={'project':project,'activity':str(line['activity'])[:200]}
            for i in range(1,8):
                try:value=Decimal(str(line.get(f'day{i}',0)))
                except (InvalidOperation,TypeError):raise ValidationError({'lines':['Enter numeric hours.']})
                if not value.is_finite() or value<0:raise ValidationError({'lines':['Hours cannot be negative.']})
                if value>10:raise ValidationError({'lines':['Please enter up to 10 hr.']})
                if value.as_tuple().exponent < -2:raise ValidationError({'lines':['Use at most two decimal places.']})
                if days[i-1]['disabled'] and value!=0:raise ValidationError({'lines':['Hours must be zero on non-working days and full-day leave.']})
                values[f'day{i}']=value
            cleaned.append(values)
        row=row or Timesheet(user=user,start_date=start,end_date=start+timedelta(days=6))
        row.approval_status='Pending';row.save(actor=request.user)
        for old in row.lines.filter(is_deleted=False):old.delete(actor=request.user)
        for data in cleaned:TimesheetLine(timesheet=row,**data).save(actor=request.user)
        TimesheetLog(timesheet=row,actor=request.user,action='Saved').save(actor=request.user)
        return Response(self.payload(request,user,start))

class LogView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,pk):
        require_menu(request.user,82)
        row=get_object_or_404(Timesheet.objects,pk=pk)
        if row.user_id!=request.user.pk and not is_hr(request.user):raise PermissionDenied()
        return Response(model_serializer(TimesheetLog,request.user)(TimesheetLog.objects.filter(timesheet=row),many=True).data)
