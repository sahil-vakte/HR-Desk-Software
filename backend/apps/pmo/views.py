from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.core.access import require_menu, is_hr
from apps.core.api import model_serializer
from .models import Query, QueryReply

class QueryReplies(APIView):
    permission_classes=[IsAuthenticated]
    def context(self,request,pk):
        require_menu(request.user,79)
        query=get_object_or_404(Query.objects,pk=pk)
        if query.employee_id!=request.user.pk and not is_hr(request.user):raise PermissionDenied()
        return query
    def get(self,request,pk):
        query=self.context(request,pk)
        return Response(model_serializer(QueryReply,request.user)(QueryReply.objects.filter(query=query).order_by('created_at'),many=True).data)
    @transaction.atomic
    def post(self,request,pk):
        query=self.context(request,pk)
        if query.status=='Closed':raise ValidationError({'message':['This query is closed.']})
        import bleach
        message=bleach.clean(str(request.data.get('message','')),tags=['p','strong','em','ul','ol','li','br'],strip=True)
        if not message.strip():raise ValidationError({'message':['Please enter message.']})
        reply=QueryReply(query=query,author=request.user,message=message)
        reply.save(actor=request.user)
        return Response(model_serializer(QueryReply,request.user)(reply).data,status=201)
