from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from apps.core.access import require_super
from apps.core.models import AuditEvent
from .models import User, Role, MenuItem, RolePermission

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    class Meta:
        model=User
        fields=['id','first_name','last_name','email','username','phone','role','is_active','password']
        read_only_fields=['id']
    def validate_email(self,value):
        qs=User.objects.filter(email__iexact=value.strip())
        if self.instance:qs=qs.exclude(pk=self.instance.pk)
        if qs.exists():raise serializers.ValidationError('Email already exist please change email .')
        return value.strip().lower()
    def validate(self,data):
        if not self.instance and not data.get('password'):raise serializers.ValidationError({'password':['Password is required.']})
        if data.get('password'):validate_password(data['password'],self.instance)
        if self.instance and self.instance.pk==self.context['request'].user.pk:
            if data.get('is_active') is False or ('role' in data and data['role'].pk!=1):raise serializers.ValidationError({'role':['You cannot remove your own administrator access.']})
        return data
    def create(self,data):
        password=data.pop('password')
        user=User(**data)
        user.set_password(password)
        user.save()
        return user
    def update(self,instance,data):
        password=data.pop('password',None)
        for key,value in data.items():setattr(instance,key,value)
        if password:instance.set_password(password)
        instance.auth_version+=1
        instance.save()
        return instance

class RoleSerializer(serializers.ModelSerializer):
    permissions=serializers.ListField(child=serializers.IntegerField(),required=False)
    class Meta:
        model=Role
        fields=['id','title','slug','status','permissions']
        read_only_fields=['id']
    def to_representation(self,instance):
        data={'id':instance.pk,'title':instance.title,'slug':instance.slug,'status':instance.status}
        data['permissions']=list(instance.grants.filter(is_deleted=False).values_list('menu_item_id',flat=True))
        return data
    def validate_permissions(self,value):
        if len(set(value))!=len(value) or MenuItem.objects.filter(pk__in=value).count()!=len(value):raise serializers.ValidationError('Invalid menu permissions.')
        return value
    def validate(self,data):
        if self.instance and self.instance.pk==1 and data.get('status') is False:raise serializers.ValidationError({'status':['The administrator role must remain active.']})
        return data
    def create(self,data):return self.update(Role(),data)
    def update(self,instance,data):
        permissions=data.pop('permissions',None)
        actor=self.context['request'].user
        for key,value in data.items():setattr(instance,key,value)
        instance.save(actor=actor)
        if permissions is not None:
            existing={x.menu_item_id:x for x in RolePermission.all_objects.filter(role=instance)}
            for code,row in existing.items():
                if code not in permissions and not row.is_deleted:row.delete(actor=actor)
            for code in permissions:
                row=existing.get(code) or RolePermission(role=instance,menu_item_id=code)
                row.is_deleted=False;row.deleted_at=None;row.status=True
                row.save(actor=actor)
        return instance

class AdminViewSet(viewsets.ModelViewSet):
    permission_classes=[IsAuthenticated]
    def initial(self,request,*args,**kwargs):
        super().initial(request,*args,**kwargs)
        require_super(request.user)
    def perform_create(self,serializer):
        with transaction.atomic():
            item=serializer.save()
            AuditEvent.objects.create(actor=self.request.user,entity=item._meta.label_lower,entity_id=str(item.pk),action='create',after={'id':item.pk})
    def perform_update(self,serializer):
        with transaction.atomic():
            item=serializer.save()
            AuditEvent.objects.create(actor=self.request.user,entity=item._meta.label_lower,entity_id=str(item.pk),action='update',after={'id':item.pk})
    def perform_destroy(self,instance):
        if isinstance(instance,Role):
            if User.objects.filter(role=instance,is_deleted=False).exists():raise ValidationError({'role':['This role is in use.']})
            instance.delete(actor=self.request.user)
        else:
            if instance.pk==self.request.user.pk:raise ValidationError({'user':['You cannot delete your own account.']})
            instance.is_deleted=True;instance.is_active=False;instance.deleted_at=timezone.now();instance.auth_version+=1
            instance.save()
            AuditEvent.objects.create(actor=self.request.user,entity='accounts.user',entity_id=str(instance.pk),action='delete')

class UsersViewSet(AdminViewSet):
    serializer_class=UserSerializer
    queryset=User.objects.filter(is_deleted=False).order_by('id')

class RolesViewSet(AdminViewSet):
    serializer_class=RoleSerializer
    queryset=Role.objects.all().order_by('id')

class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model=MenuItem
        fields=['id','title','route','parent','is_menu','order','status']

class MenusViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes=[IsAuthenticated]
    serializer_class=MenuSerializer
    def get_queryset(self):
        require_super(self.request.user)
        return MenuItem.objects.order_by('order','id')
