import hashlib
import json
import secrets
from datetime import timedelta
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from apps.core.access import require_menu
from apps.core.api import model_serializer
from .models import Applicant, CandidateInvitation, TechnicalQuestion, CvEvaluation, InterviewNote, ApplicantDocument

class CandidateSend(APIView):
    permission_classes=[IsAuthenticated]
    @transaction.atomic
    def post(self,request,pk,kind):
        require_menu(request.user,47)
        applicant=get_object_or_404(Applicant.objects,pk=pk)
        if kind not in ['test','cif','reference']:raise ValidationError({'kind':['Invalid invitation type.']})
        questions={}
        if kind=='test':
            available=list(TechnicalQuestion.objects.filter(status=True,job_roles=applicant.job_role))
            if len(available)<20:raise ValidationError({'questions':['Configure at least 20 active questions for this role.']})
            selected=secrets.SystemRandom().sample(available,20)
            questions={'items':[{'id':q.pk,'type':q.type,'question':q.question,'options':[q.option_a,q.option_b,q.option_c,q.option_d],'answer':q.correct_answer} for q in selected]}
        token=secrets.token_urlsafe(48)
        invite=CandidateInvitation(applicant=applicant,kind=kind,digest=hashlib.sha256(token.encode()).hexdigest(),expires_at=timezone.now()+timedelta(days=7),questions=questions)
        invite.save(actor=request.user)
        link=f'{settings.FRONTEND_ORIGIN}/{kind}/{token}'
        send_mail('HRDESK candidate invitation',f'Please complete your {kind}: {link}\nThis link expires in seven days.',settings.DEFAULT_FROM_EMAIL,[applicant.email])
        return Response({'message':'Invitation sent.','expires_at':invite.expires_at})

@method_decorator(csrf_protect,name='dispatch')
class PublicCandidate(APIView):
    permission_classes=[AllowAny]
    authentication_classes=[]
    def invitation(self,token):
        row=CandidateInvitation.objects.filter(digest=hashlib.sha256(token.encode()).hexdigest(),expires_at__gt=timezone.now(),consumed_at=None).first()
        if not row:raise ValidationError({'token':['This link has expired or has already been used.']})
        return row
    def get(self,request,token):
        row=self.invitation(token)
        questions=[{k:v for k,v in q.items() if k!='answer'} for q in row.questions.get('items',[])]
        return Response({'kind':row.kind,'questions':questions})
    @transaction.atomic
    def post(self,request,token):
        row=self.invitation(token)
        if row.kind=='test':
            answers=request.data.get('answers')
            ids={str(q['id']) for q in row.questions['items']}
            if not isinstance(answers,dict) or set(answers)!=ids:raise ValidationError({'answers':['Please answer all 20 questions.']})
        else:
            answers=request.data.get('answers')
            if not isinstance(answers,dict) or not answers:raise ValidationError({'answers':['Please complete the form.']})
        if len(json.dumps(answers))>100000:raise ValidationError({'answers':['Submission is too large.']})
        row.answers=json.dumps(answers);row.consumed_at=timezone.now();row.save()
        return Response({'message':'Thank you. Your response has been submitted.'})

class Evaluation(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,pk):
        require_menu(request.user,47)
        applicant=get_object_or_404(Applicant.objects,pk=pk)
        row=CvEvaluation.objects.filter(applicant=applicant).first()
        return Response(model_serializer(CvEvaluation,request.user)(row).data if row else {})
    @transaction.atomic
    def put(self,request,pk):
        require_menu(request.user,47)
        applicant=get_object_or_404(Applicant.objects,pk=pk)
        data=request.data.copy();data['applicant']=applicant.pk
        ratings=data.get('ratings')
        if not isinstance(ratings,list) or len(ratings)!=8 or any(not isinstance(r,dict) or type(r.get('rating')) is not int or not 1<=r['rating']<=5 for r in ratings):raise ValidationError({'ratings':['Provide eight ratings, each between 1 and 5, with comments.']})
        row=CvEvaluation.objects.filter(applicant=applicant).first()
        serializer=model_serializer(CvEvaluation,request.user)(row,data=data)
        serializer.is_valid(raise_exception=True)
        row=row or CvEvaluation(applicant=applicant)
        for k,v in serializer.validated_data.items():setattr(row,k,v)
        row.save(actor=request.user)
        return Response(model_serializer(CvEvaluation,request.user)(row).data)

class ParseCV(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,pk):
        from pathlib import Path
        from pypdf import PdfReader
        import zipfile
        from xml.etree import ElementTree
        require_menu(request.user,47)
        applicant=get_object_or_404(Applicant.objects,pk=pk)
        if not applicant.cv_file:raise ValidationError({'cv_file':['Upload a CV first.']})
        path=Path(settings.MEDIA_ROOT)/applicant.cv_file.stored_name
        if path.suffix.lower()=='.pdf':
            try:text='\n'.join(page.extract_text() or '' for page in PdfReader(path).pages)
            except Exception:raise ValidationError({'cv_file':['Unable to extract this PDF.']})
        elif path.suffix.lower()=='.docx':
            try:
                with zipfile.ZipFile(path) as z:root=ElementTree.fromstring(z.read('word/document.xml'))
                text=' '.join(root.itertext())
            except Exception:raise ValidationError({'cv_file':['Unable to extract this DOCX file.']})
        else:raise ValidationError({'cv_file':['Local CV text extraction supports PDF and DOCX. Configure an external parser for other formats.']})
        applicant.cv_text=text[:200000];applicant.save(actor=request.user)
        return Response({'cv_text':applicant.cv_text,'message':'CV text extracted. Review before use.'})

class ApplicantSection(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,pk,section,panel=None):
        require_menu(request.user,47)
        applicant=get_object_or_404(Applicant.objects,pk=pk)
        if section=='documents':return Response(model_serializer(ApplicantDocument,request.user)(ApplicantDocument.objects.filter(applicant=applicant),many=True).data)
        row=InterviewNote.objects.filter(applicant=applicant,panel=panel).first()
        return Response(model_serializer(InterviewNote,request.user)(row).data if row else {})
    @transaction.atomic
    def post(self,request,pk,section,panel=None):
        require_menu(request.user,47)
        applicant=get_object_or_404(Applicant.objects,pk=pk)
        data=request.data.copy();data['applicant']=applicant.pk
        model=ApplicantDocument if section=='documents' else InterviewNote
        if model==InterviewNote:
            if panel not in [1,2,3]:raise ValidationError({'panel':['Choose panel 1, 2 or 3.']})
            data.update(panel=panel,interviewer=request.user.pk)
        row=InterviewNote.objects.filter(applicant=applicant,panel=panel).first() if model==InterviewNote else None
        serializer=model_serializer(model,request.user)(row,data=data);serializer.is_valid(raise_exception=True)
        row=row or model()
        for key,value in serializer.validated_data.items():setattr(row,key,value)
        row.save(actor=request.user)
        return Response(model_serializer(model,request.user)(row).data,status=201)
    def put(self,request,pk,section,panel=None):return self.post(request,pk,section,panel)
