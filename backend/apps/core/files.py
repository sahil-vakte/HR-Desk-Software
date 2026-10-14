import hashlib
import io
import mimetypes
from pathlib import Path
import uuid
import zipfile
from django.apps import apps
from django.conf import settings
from django.http import FileResponse
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
from .models import PrivateFile, AuditEvent
from .access import has_menu, is_hr
from .registry import RESOURCES

ALLOWED={'pdf','doc','docx','xls','xlsx','csv','png','jpg','jpeg'}

def check_upload(upload):
    ext=Path(upload.name).suffix.lower().lstrip('.')
    if ext not in ALLOWED:raise ValidationError({'file':['Allowed file types: pdf, doc, docx, xls, xlsx, csv, png, jpg, jpeg.']})
    if upload.size>10*1024*1024:raise ValidationError({'file':['File must be 10 MB or smaller']})
    content=upload.read()
    good=False
    if ext=='pdf':good=content.startswith(b'%PDF-')
    elif ext in ['doc','xls']:good=content.startswith(bytes.fromhex('d0cf11e0a1b11ae1'))
    elif ext in ['docx','xlsx']:
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                good='[Content_Types].xml' in z.namelist() and any(n.startswith('word/' if ext=='docx' else 'xl/') for n in z.namelist())
                good=good and sum(i.file_size for i in z.infolist())<100*1024*1024
        except zipfile.BadZipFile:good=False
    elif ext=='csv':
        try:content.decode('utf-8-sig');good=b'\x00' not in content
        except UnicodeDecodeError:good=False
    else:
        from PIL import Image
        try:
            img=Image.open(io.BytesIO(content));img.verify()
            good=img.format==('PNG' if ext=='png' else 'JPEG')
        except Exception:good=False
    if not good:raise ValidationError({'file':['File content does not match its permitted file type.']})
    return ext,content

class UploadView(APIView):
    permission_classes=[IsAuthenticated]
    parser_classes=[MultiPartParser,FormParser]
    def post(self,request):
        purpose=request.data.get('purpose','')
        menu={'employee':71,'employee-admin':29,'wsr':78,'query':79,'project':65,'policy':30,'ho':83,'recruitment':47,'newsletter':77,'settings':40}.get(purpose)
        if not menu or not has_menu(request.user,menu):raise PermissionDenied()
        if purpose in ['employee-admin','policy','ho','recruitment','newsletter','settings'] and not is_hr(request.user):raise PermissionDenied()
        upload=request.FILES.get('file')
        if not upload:raise ValidationError({'file':['Please select attachment file.']})
        ext,content=check_upload(upload)
        root=Path(settings.MEDIA_ROOT);root.mkdir(parents=True,exist_ok=True,mode=0o700)
        name=f'{uuid.uuid4().hex}.{ext}';path=root/name
        path.write_bytes(content);path.chmod(0o600)
        try:
            with transaction.atomic():
                item=PrivateFile(owner=request.user,original_name=Path(upload.name).name,stored_name=name,
                    content_type=mimetypes.guess_type(name)[0] or 'application/octet-stream',size=len(content),sha256=hashlib.sha256(content).hexdigest(),purpose=purpose)
                item.save(actor=request.user)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return Response({'id':item.pk,'name':item.original_name,'size':item.size},status=201)


def may_download(user,file):
    if file.owner_id==user.pk:return True
    from .access import require_menu
    from .api import ResourceViewSet
    # Authorise against every attached object's actual scoped queryset.
    from rest_framework.request import Request
    from rest_framework.test import APIRequestFactory, force_authenticate
    for key,spec in RESOURCES.items():
        if not has_menu(user,spec.menu):continue
        model=apps.get_model(spec.model)
        fields=[f for f in model._meta.fields if getattr(f,'related_model',None)==PrivateFile]
        if not fields:continue
        for field in fields:
            for instance in model.objects.filter(**{field.name:file}):
                if spec.scope=='read_all' or spec.scope=='readonly':return True
                if spec.scope=='admin' and is_hr(user):return True
                if spec.scope in ['self','leave'] and (is_hr(user) or getattr(instance,spec.owner+'_id')==user.pk):return True
                if spec.scope=='projects' and (is_hr(user) or instance.members.filter(pk=user.pk).exists()):return True
    from apps.employees.models import EmployeeDocument, PaperworkDocument
    for model in [EmployeeDocument,PaperworkDocument]:
        for doc in model.objects.filter(file=file):
            if (doc.user_id==user.pk and has_menu(user,71)) or (is_hr(user) and has_menu(user,29)):return True
    from apps.projects.models import ProjectDocument
    for doc in ProjectDocument.objects.filter(file=file):
        if has_menu(user,65) and (is_hr(user) or doc.project.members.filter(pk=user.pk).exists()):return True
    return False

class DownloadView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,pk):
        file=PrivateFile.objects.filter(pk=pk).first()
        if not file:raise NotFound()
        if not may_download(request.user,file):raise PermissionDenied()
        path=Path(settings.MEDIA_ROOT)/file.stored_name
        if not path.is_file():raise NotFound()
        AuditEvent.objects.create(actor=request.user,entity='core.privatefile',entity_id=str(pk),action='download')
        response=FileResponse(path.open('rb'),as_attachment=True,filename=file.original_name,content_type=file.content_type)
        response['Cache-Control']='no-store'
        return response
