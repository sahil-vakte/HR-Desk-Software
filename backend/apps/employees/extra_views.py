from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.core.access import require_menu, require_hr, is_hr
from apps.core.api import model_serializer
from apps.accounts.models import User
from apps.reports.views import export_rows
from .models import Employee, EmergencyContact

class NextId(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        require_menu(request.user,29);require_hr(request.user)
        last=Employee.all_objects.order_by('-pk').first()
        return Response({'employee_code':f'KN{(last.pk+1 if last else 1):03d}'})

class CheckEmail(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        require_menu(request.user,29);require_hr(request.user)
        return Response({'exists':User.objects.filter(email__iexact=request.query_params.get('email','')).exists()})

class EmployeeExport(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        require_menu(request.user,29);require_hr(request.user)
        rows=[{'Employee ID':e.employee_code,'Name':e.user.get_full_name(),'Email':e.user.email,'Joining date':str(e.date_of_joining),'Status':e.employee_status} for e in Employee.objects.select_related('user')]
        return export_rows(rows,'Employees','csv')

class EmergencyPDF(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,employee_id):
        require_menu(request.user,29);require_hr(request.user)
        employee=get_object_or_404(Employee.objects,pk=employee_id)
        rows=list(EmergencyContact.objects.filter(user=employee.user).values('name','relationship','home_phone','mobile','email','address'))
        return export_rows(rows,'Emergency contacts','pdf')

class JobReporting(APIView):
    permission_classes=[IsAuthenticated]
    def context(self,request,employee_id):
        employee=get_object_or_404(Employee.objects,pk=employee_id)
        if is_hr(request.user):require_menu(request.user,29)
        else:
            require_menu(request.user,71)
            if employee.user_id!=request.user.pk or request.method!='GET':raise PermissionDenied()
        return employee
    def get(self,request,employee_id,section):
        employee=self.context(request,employee_id)
        if section=='subordinates':return Response([{'id':e.user_id,'name':e.user.get_full_name()} for e in Employee.objects.filter(reports_to=employee.user).select_related('user')])
        if section=='supervisors':return Response({'reports_to':employee.reports_to_id})
        return Response({key:getattr(employee,key) for key in ['job_title_id','employment_type_id','date_of_joining','sub_unit_id','location']})
    @transaction.atomic
    def put(self,request,employee_id,section):
        employee=self.context(request,employee_id)
        if section=='supervisors':
            manager=get_object_or_404(User,pk=request.data.get('reports_to'),is_active=True,is_deleted=False)
            if manager.pk==employee.user_id:raise ValidationError({'reports_to':['An employee cannot report to themselves.']})
            # Walk the reporting chain to prevent cycles.
            seen={employee.user_id};current=manager
            while current:
                if current.pk in seen:raise ValidationError({'reports_to':['Reporting lines cannot contain a cycle.']})
                seen.add(current.pk);profile=Employee.objects.filter(user=current).first();current=profile.reports_to if profile else None
            employee.reports_to=manager
        else:
            allowed={'job_title','employment_type','date_of_joining','sub_unit','location'}
            if set(request.data)-allowed:raise ValidationError({'fields':['Unsupported job field.']})
            serializer=model_serializer(Employee,request.user)(employee,data=request.data,partial=True);serializer.is_valid(raise_exception=True)
            for k,v in serializer.validated_data.items():setattr(employee,k,v)
        employee.save(actor=request.user)
        return self.get(request,employee_id,section)
    def patch(self,request,employee_id,section):return self.put(request,employee_id,section)
