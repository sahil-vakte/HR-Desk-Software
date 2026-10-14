from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from apps.core.access import require_menu, require_hr, is_hr
from apps.employees.models import Employee, EmployeeDocument
from apps.leave.models import LeaveRequest, LeaveEntitlement
from apps.holidays.models import Holiday
from apps.attendance.models import AttendanceSession
from .services import leave_usage

class Dashboard(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,variant):
        require_menu(request.user,1)
        today=timezone.localdate()
        if variant=='admin':
            require_hr(request.user)
            staff=Employee.objects.filter(status=True,deactivated_on=None)
            docs=EmployeeDocument.objects.filter(is_archived=False)
            return Response({'total_employees':staff.count(),
                'confirmed':staff.filter(employee_status='Confirm Employees').count(),
                'probation':staff.filter(employee_status='On Probation').count(),
                'notice':staff.filter(employee_status='On Notice Period').count(),
                'birthdays':[{'name':e.user.get_full_name(),'date_of_birth':str(e.date_of_birth),'phone':e.user.phone} for e in staff.filter(date_of_birth__month=today.month).select_related('user')],
                'absent':[{'name':r.user.get_full_name(),'from_date':str(r.from_date),'to_date':str(r.to_date),'status':r.status} for r in LeaveRequest.objects.filter(from_date__lte=today,to_date__gte=today,status__in=['Approve With Pay','Approve Without Pay']).select_related('user')],
                'verification_pending':[{'id':d.pk,'user':d.user_id,'file':d.file_id} for d in docs.filter(verified=False)],
                'expiring_documents':[{'id':d.pk,'user':d.user_id,'file':d.file_id,'expiry_date':str(d.expiry_date),'days_remaining':(d.expiry_date-today).days} for d in docs.filter(expiry_date__range=[today,today+timedelta(days=60)])]})
        docs=EmployeeDocument.objects.filter(user=request.user,is_archived=False,expiry_date__range=[today,today+timedelta(days=60)])
        sessions=AttendanceSession.objects.filter(user=request.user)
        stats={}
        for key,start in [('today',today),('week',today-timedelta(days=today.weekday())),('month',today.replace(day=1))]:
            stats[key]=round(sum(r.total_minutes if r.punch_out else (timezone.now()-r.punch_in).total_seconds()/60 for r in sessions.filter(date__gte=start))/60,2)
        holiday=Holiday.objects.filter(status=True,date__gte=today).order_by('date').first()
        return Response({'statistics':stats,'leave':[{'leave_type':e.leave_type.name,**leave_usage(request.user,e.leave_type)} for e in LeaveEntitlement.objects.filter(user=request.user)],
            'upcoming_holiday':{'name':holiday.name,'date':str(holiday.date)} if holiday else None,
            'expiring_documents':[{'id':d.pk,'file':d.file_id,'expiry_date':str(d.expiry_date)} for d in docs]})

class LeaveBalance(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        require_menu(request.user,56,31)
        user_id=request.query_params.get('employee',request.user.pk) if is_hr(request.user) else request.user.pk
        rows=LeaveEntitlement.objects.filter(user_id=user_id)
        if request.query_params.get('leave_year'):rows=rows.filter(leave_type__leave_year_id=request.query_params['leave_year'])
        return Response({'count':rows.count(),'next':None,'previous':None,'results':[{'id':e.pk,'leave_type':e.leave_type.name,**leave_usage(e.user,e.leave_type)} for e in rows]})
