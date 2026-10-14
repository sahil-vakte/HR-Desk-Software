from datetime import timedelta
from zoneinfo import ZoneInfo
from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from apps.core.access import require_menu
from apps.core.services import employee_for, Conflict
from apps.core.api import model_serializer
from .models import AttendanceSession

class Punch(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,operation):
        require_menu(request.user,27)
        if 'user' in request.data or 'user_id' in request.data:raise PermissionDenied()
        employee=employee_for(request.user)
        now=timezone.now()
        zone=employee.process.time_zone if employee.process else 'Europe/London'
        try:
            with transaction.atomic():
                opened=AttendanceSession.objects.select_for_update().filter(user=request.user,punch_out=None).first()
                if operation=='punch-in':
                    if opened:raise Conflict('You are already punched in.')
                    row=AttendanceSession(user=request.user,date=now.astimezone(ZoneInfo(zone)).date(),work_mode=employee.work_mode,punch_in=now)
                else:
                    if not opened:raise Conflict('There is no open attendance session.')
                    row=opened;row.punch_out=now;row.total_minutes=max(0,int((now-row.punch_in).total_seconds()/60))
                row.save(actor=request.user)
        except IntegrityError:raise Conflict('An attendance session is already open.')
        return Response(model_serializer(AttendanceSession,request.user)(row).data)

class MyAttendance(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        require_menu(request.user,27)
        rows=AttendanceSession.objects.filter(user=request.user).order_by('-punch_in')
        today=timezone.localdate()
        statistics={}
        for key,start in [('today',today),('week',today-timedelta(days=today.weekday())),('month',today.replace(day=1))]:
            statistics[key]=round(sum((r.total_minutes if r.punch_out else (timezone.now()-r.punch_in).total_seconds()/60) for r in rows.filter(date__gte=start))/60,2)
        return Response({'statistics':statistics,'count':rows.count(),'next':None,'previous':None,'results':model_serializer(AttendanceSession,request.user)(rows,many=True).data})
