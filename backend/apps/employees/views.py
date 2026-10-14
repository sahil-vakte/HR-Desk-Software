from django.apps import apps
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.core.access import require_menu, is_hr, require_hr
from apps.core.api import model_serializer
from apps.core.registry import PROFILE
from apps.accounts.admin_api import UserSerializer
from apps.core.models import AuditEvent
from .models import Employee

class EmployeeCreate(APIView):
    permission_classes=[IsAuthenticated]
    @transaction.atomic
    def post(self,request):
        require_menu(request.user,29);require_hr(request.user)
        account=request.data.get('account',{}).copy()
        if request.user.role_id!=1 and int(account.get('role',4))!=4:raise PermissionDenied()
        account.setdefault('role',4)
        user_ser=UserSerializer(data=account,context={'request':request})
        user_ser.is_valid(raise_exception=True)
        user=user_ser.save()
        data=request.data.get('profile',{}).copy()
        if not data.get('employee_code'):
            last=Employee.all_objects.order_by('-pk').first()
            data['employee_code']=f'KN{(last.pk+1 if last else 1):03d}'
        serializer=model_serializer(Employee,request.user)(data=data)
        serializer.is_valid(raise_exception=True)
        employee=Employee(user=user,**serializer.validated_data)
        employee.save(actor=request.user)
        AuditEvent.objects.create(actor=request.user,entity='accounts.user',entity_id=str(user.pk),action='create')
        return Response(model_serializer(Employee,request.user)(employee).data,status=201)

class OwnProfile(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        require_menu(request.user,71)
        employee=get_object_or_404(Employee.objects,user=request.user)
        return Response(model_serializer(Employee,request.user)(employee).data)
    def patch(self,request):
        require_menu(request.user,71)
        if set(request.data)-{'phone'}:raise PermissionDenied()
        request.user.phone=str(request.data.get('phone',''))[:40]
        request.user.save()
        AuditEvent.objects.create(actor=request.user,entity='accounts.user',entity_id=str(request.user.pk),action='update_contact')
        return Response({'phone':request.user.phone})

class ProfileSection(APIView):
    permission_classes=[IsAuthenticated]
    def context(self,request,employee_id,section):
        employee=get_object_or_404(Employee.objects,pk=employee_id)
        if section not in PROFILE:raise ValidationError({'section':['Unknown profile section.']})
        if is_hr(request.user):require_menu(request.user,29)
        else:
            require_menu(request.user,71)
            if employee.user_id!=request.user.pk:raise PermissionDenied()
            if section=='salary':raise PermissionDenied()
            if request.method!='GET' and section not in ['addresses','contact-details','emergency-contacts','documents']:raise PermissionDenied()
        return employee,apps.get_model('employees',PROFILE[section])
    def get(self,request,employee_id,section,pk=None):
        employee,model=self.context(request,employee_id,section)
        rows=model.objects.filter(user=employee.user).order_by('-pk')
        serializer=model_serializer(model,request.user)
        if pk:return Response(serializer(get_object_or_404(rows,pk=pk)).data)
        return Response({'count':rows.count(),'next':None,'previous':None,'results':serializer(rows,many=True).data})
    @transaction.atomic
    def post(self,request,employee_id,section,pk=None):
        employee,model=self.context(request,employee_id,section)
        data=request.data.copy();data['user']=employee.user_id
        serializer=model_serializer(model,request.user)(data=data)
        serializer.is_valid(raise_exception=True)
        values=dict(serializer.validated_data);values['user']=employee.user
        if not is_hr(request.user):values.pop('verified',None);values.pop('checked_date',None)
        row=model(**values);row.save(actor=request.user)
        return Response(model_serializer(model,request.user)(row).data,status=201)
    @transaction.atomic
    def patch(self,request,employee_id,section,pk):
        employee,model=self.context(request,employee_id,section)
        row=get_object_or_404(model.objects,user=employee.user,pk=pk)
        serializer=model_serializer(model,request.user)(row,data=request.data,partial=True)
        serializer.is_valid(raise_exception=True)
        for key,value in serializer.validated_data.items():
            if key!='user':setattr(row,key,value)
        row.save(actor=request.user)
        return Response(model_serializer(model,request.user)(row).data)
    def delete(self,request,employee_id,section,pk):
        employee,model=self.context(request,employee_id,section)
        row=get_object_or_404(model.objects,user=employee.user,pk=pk)
        row.delete(actor=request.user)
        return Response(status=204)

class VerifyDocument(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,employee_id,pk):
        from django.utils import timezone
        from .models import EmployeeDocument
        require_menu(request.user,29);require_hr(request.user)
        employee=get_object_or_404(Employee.objects,pk=employee_id)
        document=get_object_or_404(EmployeeDocument.objects,pk=pk,user=employee.user)
        document.verified=True;document.checked_date=timezone.localdate();document.save(actor=request.user)
        return Response({'message':'Document verified.'})

class Directory(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        require_menu(request.user,58)
        rows=Employee.objects.filter(status=True).select_related('user','job_title','sub_unit')
        return Response({'count':rows.count(),'next':None,'previous':None,'results':[{'id':e.pk,'name':e.user.get_full_name(),'job_title':e.job_title.name if e.job_title else '', 'sub_unit':e.sub_unit.name if e.sub_unit else '', 'photo':e.photo_id} for e in rows]})
