from django.apps import apps
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from .access import require_menu, require_super
from .api import model_serializer

class SettingsView(APIView):
    permission_classes=[IsAuthenticated]
    sections={'company':('Company',40),'theme':('Theme',34),'localisation':('Localisation',35),'email':('SmtpProfile',36)}
    def context(self,request,section):
        if section not in self.sections:raise ValidationError({'section':['Unknown settings section.']})
        name,menu=self.sections[section];require_menu(request.user,menu);require_super(request.user)
        return apps.get_model('core',name)
    def get(self,request,section):
        model=self.context(request,section)
        if section=='email':
            rows=model_serializer(model,request.user)(model.objects.all(),many=True).data
            for row in rows:row.pop('password',None)
            return Response(rows)
        row=model.objects.first()
        return Response(model_serializer(model,request.user)(row).data if row else {})
    @transaction.atomic
    def put(self,request,section):
        model=self.context(request,section)
        row=model.objects.filter(profile=request.data.get('profile')).first() if section=='email' else model.objects.first()
        serializer=model_serializer(model,request.user)(row,data=request.data,partial=True)
        serializer.is_valid(raise_exception=True)
        row=row or model()
        for key,value in serializer.validated_data.items():setattr(row,key,value)
        if section=='theme':
            import re
            for key in ['primary_color','secondary_color','sidebar_color']:
                if not re.fullmatch(r'#[0-9a-fA-F]{6}',getattr(row,key)):raise ValidationError({key:['Enter a six-digit hexadecimal colour.']})
        if section in ['company','localisation']:
            from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
            try:ZoneInfo(row.time_zone if section=='company' else row.timezone)
            except ZoneInfoNotFoundError:raise ValidationError({'timezone':['Choose a valid IANA timezone.']})
        row.full_clean(validate_unique=False,validate_constraints=False)
        row.save(actor=request.user)
        data=model_serializer(model,request.user)(row).data
        data.pop('password',None)
        return Response(data)
