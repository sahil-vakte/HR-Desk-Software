import csv
import io
from html import escape
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from apps.core.access import require_menu, require_hr
from apps.core.services import leave_usage


def export_rows(rows,title,kind):
    columns=list(rows[0]) if rows else ['message']
    if kind=='csv':
        stream=io.StringIO();writer=csv.writer(stream);writer.writerow(columns)
        for row in rows:
            values=[]
            for key in columns:
                value=str(row.get(key,''))
                if value.startswith(('=','+','-','@','\t','\r')):value="'"+value
                values.append(value)
            writer.writerow(values)
        response=HttpResponse('\ufeff'+stream.getvalue(),content_type='text/csv; charset=utf-8')
    elif kind=='pdf':
        from xhtml2pdf import pisa
        html='<html><head><style>@page {size: A4 landscape; margin: 1cm} body {font-family: Helvetica; font-size:9pt} td,th {padding:4pt;border-bottom:1px solid #ccc}</style></head><body><h1>'+escape(title)+'</h1><table><tr>'+''.join('<th>'+escape(c)+'</th>' for c in columns)+'</tr>'
        html+=''.join('<tr>'+''.join('<td>'+escape(str(row.get(c,'')))+'</td>' for c in columns)+'</tr>' for row in rows)+'</table></body></html>'
        stream=io.BytesIO();result=pisa.CreatePDF(html,dest=stream)
        if result.err:raise ValidationError({'export':['Unable to render PDF.']})
        response=HttpResponse(stream.getvalue(),content_type='application/pdf')
    else:raise ValidationError({'format':['Choose csv or pdf.']})
    response['Content-Disposition']=f'attachment; filename="{title.lower().replace(" ","-")}.{kind}"'
    response['Cache-Control']='no-store'
    return response

class Report(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,kind):
        code={'leave':42,'attendance':68,'pmo':85}.get(kind)
        if not code:raise ValidationError({'report':['Unknown report.']})
        require_menu(request.user,code);require_hr(request.user)
        rows=[]
        if kind=='leave':
            from apps.leave.models import LeaveEntitlement
            entries=LeaveEntitlement.objects.select_related('user','leave_type')
            if request.query_params.get('leave_year'):entries=entries.filter(leave_type__leave_year_id=request.query_params['leave_year'])
            for e in entries:rows.append({'Employee':e.user.get_full_name(),'Leave type':e.leave_type.name,**leave_usage(e.user,e.leave_type)})
        elif kind=='attendance':
            from apps.attendance.models import AttendanceSession
            entries=AttendanceSession.objects.select_related('user')
            for key in ['month','year']:
                if request.query_params.get(key):entries=entries.filter(**{'date__'+key:request.query_params[key]})
            if request.query_params.get('employee'):entries=entries.filter(user_id=request.query_params['employee'])
            rows=[{'Employee':e.user.get_full_name(),'Date':e.date.strftime('%d-%m-%Y'),'Punch in':e.punch_in.isoformat(),'Punch out':e.punch_out.isoformat() if e.punch_out else '', 'Hours':round(e.total_minutes/60,2)} for e in entries]
        else:
            from apps.pmo.models import WeeklyStatusReport
            entries=WeeklyStatusReport.objects.select_related('user')
            for key in ['month','year']:
                if request.query_params.get(key):entries=entries.filter(**{'week_start__'+key:request.query_params[key]})
            rows=[{'Employee':e.user.get_full_name(),'Week':e.week_start.strftime('%d-%m-%Y'),'Status':e.status} for e in entries]
        if request.query_params.get('export'):return export_rows(rows,kind+' report',request.query_params['export'])
        return Response({'count':len(rows),'next':None,'previous':None,'results':rows})
