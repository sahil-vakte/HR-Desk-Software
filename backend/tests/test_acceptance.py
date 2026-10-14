from datetime import date, timedelta
from decimal import Decimal
import io
import pytest
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from apps.accounts.models import User, Role, MenuItem
from apps.employees.models import Employee
from apps.masters.models import MasterItem
from apps.projects.models import Project, Task
from apps.leave.models import LeaveYear, LeaveType, LeaveEntitlement, LeaveRequest
from apps.wfh.models import WfhRequest
from apps.core.models import PrivateFile, AuditEvent
from apps.timesheets.models import Timesheet, TimesheetLine, TimesheetLog
from apps.pmo.models import Query, WeeklyStatusReport

pytestmark=pytest.mark.django_db
PASSWORD='Fictional-Test-Password7!'

@pytest.fixture
def sample():
    call_command('seed',stdout=io.StringIO())
    users=[]
    process=MasterItem.objects.get(kind='processes',name='UK')
    for i,role in enumerate([1,4,4]):
        user=User.objects.create_user(username=f'test{i}',email=f'test{i}@example.invalid',password=PASSWORD,role_id=role,first_name=f'Fictional{i}')
        Employee(user=user,employee_code=f'KN{i+1:03}',date_of_joining=date(2020,1,1),process=process).save()
        users.append(user)
    admin,a,b=users
    project=Project(name='Fictional project',start_date=date(2020,1,1),lead=a);project.save();project.members.add(a)
    start=date.today()+timedelta(days=7)
    start+=timedelta(days=(7-start.weekday())%7)
    ly=LeaveYear(from_date=date(start.year,1,1),to_date=date(start.year,12,31),process=process);ly.save()
    lt=LeaveType(leave_year=ly,name='Fictional annual',process=process,allocation_per_year=25);lt.save()
    for user in [a,b]:LeaveEntitlement(user=user,leave_type=lt,assigned=25).save()
    return {'admin':admin,'a':a,'b':b,'project':project,'start':start,'type':lt,'year':ly}

def client(user):
    c=APIClient();c.force_authenticate(user);return c

def wfh(sample,who='a'):
    r=client(sample[who]).post('/api/v1/wfh-requests/',{'duration':'Full Day','date':str(sample['start']),'comment':'Fictional'},format='json')
    assert r.status_code==201,r.data
    return r.data

def leave(sample):
    r=client(sample['a']).post('/api/v1/leave/requests/',{'leave_type':sample['type'].pk,'duration':'Full Day','from_date':str(sample['start']),'to_date':str(sample['start'])},format='json')
    assert r.status_code==201,r.data
    return r.data

def sheet(sample,**overrides):
    line={'project':sample['project'].pk,'activity':'Implementation',**{f'day{i}':0 for i in range(1,8)},'day1':8}
    line.update(overrides)
    return client(sample['a']).put(f"/api/v1/timesheets/{sample['a'].pk}/{sample['start']}/",{'lines':[line]},format='json')


def test_001_login_success(sample):
    c=APIClient(enforce_csrf_checks=True)
    csrf=c.get('/api/v1/auth/csrf/').json()['csrfToken']
    response=c.post('/api/v1/auth/login/',{'email':sample['a'].email,'password':PASSWORD},format='json',HTTP_X_CSRFTOKEN=csrf)
    assert response.status_code==200,response.data
    assert c.get('/api/v1/session/').status_code==200


def test_002_login_failure(sample):
    response=APIClient().post('/api/v1/auth/login/',{'email':sample['a'].email,'password':'wrong'},format='json')
    assert response.status_code==422
    assert response.data['errors']['email']==['These credentials do not match our records.']


def test_003_logout(sample):
    c=APIClient();c.post('/api/v1/auth/login/',{'email':sample['a'].email,'password':PASSWORD},format='json')
    assert c.post('/api/v1/auth/logout/').status_code==204
    assert c.get('/api/v1/session/').status_code==401


def test_004_menu_per_role(sample):
    response=client(sample['a']).get('/api/v1/session/').data
    ids=response['permissions']
    assert 29 not in ids and all(code in ids for code in [1,71,16,55,27,30,65,66,77,78,79,80,82,52])


def test_005_manager_hidden(sample):
    response=client(sample['a']).get('/api/v1/session/').data
    assert not any(x['menu_id']==46 for x in response['menu'])


def test_006_manager_menu_and_scope(sample):
    employee=Employee.objects.get(user=sample['b']);employee.reports_to=sample['a'];employee.save()
    response=client(sample['a']).get('/api/v1/session/').data
    assert any(x['menu_id']==46 for x in response['menu'])
    assert client(sample['a']).get('/api/v1/leave/requests/team/').status_code==200


def test_007_punch_cycle(sample):
    c=client(sample['a'])
    assert c.post('/api/v1/attendance/punch-in/').status_code==200
    assert c.post('/api/v1/attendance/punch-out/').status_code==200
    result=c.get('/api/v1/attendance/me/').data
    assert result['count']==1 and result['results'][0]['punch_out'] is not None


def test_008_double_punch(sample):
    c=client(sample['a']);c.post('/api/v1/attendance/punch-in/')
    assert c.post('/api/v1/attendance/punch-in/').status_code==409


def test_009_empty_leave(sample):
    r=client(sample['a']).post('/api/v1/leave/requests/',{},format='json')
    assert r.status_code==422
    assert r.data['errors']['leave_type']==['Please select leave type.']
    assert r.data['errors']['from_date']==['Please select from date.']
    assert r.data['errors']['to_date']==['Please select to date.']


def test_010_over_balance(sample):
    ent=LeaveEntitlement.objects.get(user=sample['a']);ent.assigned=0;ent.save()
    r=client(sample['a']).post('/api/v1/leave/requests/',{'leave_type':sample['type'].pk,'from_date':str(sample['start']),'to_date':str(sample['start'])},format='json')
    assert r.status_code==422
    assert 'You only left 0 balance leaves' in str(r.data)
    assert LeaveRequest.objects.count()==0


def test_011_paid_leave(sample):
    row=leave(sample)
    r=client(sample['admin']).post(f"/api/v1/leave/requests/{row['id']}/approve/",{},format='json')
    assert r.status_code==200,r.data
    assert r.data['status']=='Approve With Pay'
    assert client(sample['a']).get('/api/v1/leave/balance/').data['results'][0]['used']==1


def test_012_leave_reject_reason(sample):
    row=leave(sample)
    r=client(sample['admin']).post(f"/api/v1/leave/requests/{row['id']}/reject/",{},format='json')
    assert r.status_code==422
    assert LeaveRequest.objects.get(pk=row['id']).status=='Pending'


def test_013_wfh_empty(sample):
    r=client(sample['a']).post('/api/v1/wfh-requests/',{},format='json')
    assert r.status_code==422
    assert r.data['errors']['duration']==['Please select duration.']
    assert r.data['errors']['date']==['Please select date.']


def test_014_wfh_pending(sample):assert wfh(sample)['status']=='Pending'

def test_015_duplicate_wfh(sample):
    wfh(sample)
    r=client(sample['a']).post('/api/v1/wfh-requests/',{'date':str(sample['start']),'duration':'Full Day'},format='json')
    assert r.status_code==409
    assert WfhRequest.objects.count()==1


def test_016_wfh_approval(sample):
    row=wfh(sample);r=client(sample['admin']).post(f"/api/v1/wfh-requests/{row['id']}/approve/")
    assert r.status_code==200 and r.data['status']=='Approved'


def test_017_wfh_reason_required(sample):
    row=wfh(sample);r=client(sample['admin']).post(f"/api/v1/wfh-requests/{row['id']}/reject/")
    assert r.status_code==422 and 'Please enter some reason for rejection' in str(r.data)


def test_018_wfh_rejection(sample):
    row=wfh(sample);r=client(sample['admin']).post(f"/api/v1/wfh-requests/{row['id']}/reject/",{'reason':'Coverage required'},format='json')
    assert r.data['status']=='Rejected' and r.data['rejection_reason']=='Coverage required'


def test_019_wfh_scoping(sample):
    a=wfh(sample);wfh(sample,'b')
    r=client(sample['a']).get('/api/v1/wfh-requests/')
    assert [x['id'] for x in r.data['results']]==[a['id']]


def test_020_task_creation(sample):
    r=client(sample['a']).post('/api/v1/tasks/',{'project':sample['project'].pk,'name':'Fictional task','assignees':[sample['a'].pk]},format='json')
    assert r.status_code==201,r.data
    assert r.data['status']=='To Do'


def test_021_task_status(sample):
    task=Task(project=sample['project'],name='Fictional task');task.save()
    r=client(sample['a']).patch(f'/api/v1/tasks/{task.pk}/',{'status':'In progress'},format='json')
    assert r.status_code==200 and r.data['status']=='In progress'


def test_022_assignable_members(sample):
    r=client(sample['a']).get(f"/api/v1/projects/{sample['project'].pk}/assignable-users/")
    assert [x['id'] for x in r.data]==[sample['a'].pk]
    r=client(sample['a']).post('/api/v1/tasks/',{'project':sample['project'].pk,'name':'Bad assignee','assignees':[sample['b'].pk]},format='json')
    assert r.status_code==422


def test_023_nonmember_projects(sample):
    assert client(sample['b']).get('/api/v1/projects/').data['count']==0


def test_024_timesheet_max(sample):
    r=sheet(sample,day1=25)
    assert r.status_code==422 and 'Please enter up to 10 hr.' in str(r.data)


def test_025_timesheet_negative(sample):assert sheet(sample,day1=-2).status_code==422

def test_026_timesheet_project(sample):assert sheet(sample,project=None).status_code==422

def test_027_no_orphan_lines(sample):
    assert sheet(sample).status_code==200
    r=client(sample['a']).get(f"/api/v1/timesheets/{sample['a'].pk}/{sample['start']+timedelta(days=7)}/")
    assert r.status_code==200 and r.data['lines']==[]


def test_028_weekends_disabled(sample):
    r=client(sample['a']).get(f"/api/v1/timesheets/{sample['a'].pk}/{sample['start']}/")
    assert all(day['disabled'] for day in r.data['days'][5:])
    assert sheet(sample,day6=1).status_code==422


def test_029_timesheet_accept(sample):
    r=sheet(sample);assert r.status_code==200,r.data
    r=client(sample['admin']).post(f"/api/v1/timesheets/{r.data['id']}/accept/")
    assert r.status_code==200,r.data
    assert r.data['approval_status']=='Accepted'
    assert TimesheetLog.objects.filter(action='Accepted').exists()


def test_030_timesheet_reject(sample):
    r=sheet(sample)
    r=client(sample['admin']).post(f"/api/v1/timesheets/{r.data['id']}/reject/",{'reason':'Please correct activity'},format='json')
    assert r.status_code==200 and r.data['approval_status']=='Rejected'
    assert TimesheetLog.objects.filter(comment='Please correct activity').exists()


def test_031_wsr_empty(sample):
    r=client(sample['a']).post('/api/v1/wsr/',{},format='json')
    assert r.status_code==422
    assert r.data['errors']['week_start']==['Please select date.']
    assert r.data['errors']['attachment']==['Please select attachment file.']


def test_032_wsr_submit(sample):
    file=PrivateFile(owner=sample['a'],original_name='report.pdf',stored_name='fictional.pdf',content_type='application/pdf',size=5,sha256='a'*64,purpose='wsr');file.save()
    r=client(sample['a']).post('/api/v1/wsr/',{'week_start':str(sample['start']),'attachment':file.pk},format='json')
    assert r.status_code==201,r.data
    assert r.data['status']=='Submitted'


def test_033_executable_rejected(sample):
    r=client(sample['a']).post('/api/v1/files/',{'file':SimpleUploadedFile('bad.exe',b'MZfake'),'purpose':'wsr'},format='multipart')
    assert r.status_code==422
    assert PrivateFile.objects.count()==0


def test_034_query_required(sample):
    r=client(sample['a']).post('/api/v1/queries/',{},format='json')
    assert r.status_code==422
    assert r.data['errors']['subject']==['Please enter subject.']
    assert r.data['errors']['priority']==['Please select priority.']
    assert r.data['errors']['message']==['Please enter message.']


def test_035_query_code(sample):
    r=client(sample['a']).post('/api/v1/queries/',{'subject':'Fictional question','priority':'Low','message':'Please help'},format='json')
    assert r.status_code==201,r.data
    assert r.data['status']=='In-Progress' and r.data['query_code'].startswith('Qexample')


def test_036_reply_close(sample):
    query=Query(query_code='Qexample01',employee=sample['a'],created_by=sample['a'],subject='Fictional',message='Help');query.save()
    c=client(sample['admin'])
    assert c.post(f'/api/v1/queries/{query.pk}/replies/',{'message':'Reply'},format='json').status_code==201
    r=c.post(f'/api/v1/queries/{query.pk}/close/')
    assert r.status_code==200 and r.data['status']=='Closed'


def test_037_master_required(sample):
    r=client(sample['admin']).post('/api/v1/masters/skills/',{},format='json')
    assert r.status_code==422 and r.data['errors']['name']==['Please enter the name.']


def test_038_master_lifecycle(sample):
    c=client(sample['admin'])
    r=c.post('/api/v1/masters/skills/',{'name':'Fictional skill'},format='json');assert r.status_code==201,r.data
    pk=r.data['id']
    assert c.patch(f'/api/v1/masters/skills/{pk}/',{'name':'Changed fictional skill','status':False},format='json').status_code==200
    assert c.delete(f'/api/v1/masters/skills/{pk}/').status_code==204
    assert MasterItem.all_objects.get(pk=pk).is_deleted


def test_039_master_duplicate(sample):
    c=client(sample['admin']);c.post('/api/v1/masters/skills/',{'name':'Fictional skill'},format='json')
    assert c.post('/api/v1/masters/skills/',{'name':'FICTIONAL SKILL'},format='json').status_code==409


def test_040_leave_type_required(sample):
    r=client(sample['admin']).post('/api/v1/leave-types/',{},format='json')
    assert r.status_code==422
    assert r.data['errors']['name']==['Please enter the name.']
    assert r.data['errors']['allocation_per_year']==['Please enter allocation/year leaves.']


def test_041_leave_year_order(sample):
    r=client(sample['admin']).post('/api/v1/leave-years/',{'from_date':'2028-12-31','to_date':'2028-01-01','process':sample['year'].process_id},format='json')
    assert r.status_code==422

@pytest.mark.parametrize('path,method,payload',[
 ('/api/v1/employees/','get',None),
 ('/api/v1/employees/1/salary/','post',{}),
 ('/api/v1/leave/requests/manage/','get',None),
 ('/api/v1/wfh-requests/manage/','get',None),
 ('/api/v1/timesheets/manage/','get',None),
 ('/api/v1/settings/company/','put',{}),
 ('/api/v1/admin/users/','get',None),
 ('/api/v1/admin/roles/','get',None),
],ids=[f'TEST-{n:03}' for n in range(42,50)])
def test_042_to_049_admin_permissions(sample,path,method,payload):
    r=getattr(client(sample['a']),method)(path,payload,format='json')
    assert r.status_code==403,r.data


def test_050_safe_lookup(sample):
    r=client(sample['a']).get('/api/v1/lookups/users/')
    assert r.status_code==200 and all(set(row)=={'id','name'} for row in r.data)


def test_051_punch_identity(sample):
    assert client(sample['a']).post('/api/v1/attendance/punch-in/',{'user_id':sample['b'].pk},format='json').status_code==403


def test_052_https(sample):
    with override_settings(SECURE_SSL_REDIRECT=True,SECURE_HSTS_SECONDS=31536000):
        c=APIClient()
        assert c.get('/api/v1/health/').status_code==301
        assert '31536000' in c.get('/api/v1/health/',secure=True)['Strict-Transport-Security']


def test_053_cookie_flags(sample):
    with override_settings(SESSION_COOKIE_SECURE=True):
        c=APIClient();r=c.post('/api/v1/auth/login/',{'email':sample['a'].email,'password':PASSWORD},format='json',secure=True)
        assert r.status_code==200,r.data
        assert r.cookies['sessionid']['httponly'] and r.cookies['sessionid']['secure']


def test_054_lockout(sample):
    c=APIClient()
    for _ in range(5):assert c.post('/api/v1/auth/login/',{'email':sample['a'].email,'password':'wrong'},format='json').status_code==422
    assert c.post('/api/v1/auth/login/',{'email':sample['a'].email,'password':'wrong'},format='json').status_code==429


def test_055_audit_transition(sample):
    row=wfh(sample)
    client(sample['admin']).post(f"/api/v1/wfh-requests/{row['id']}/approve/")
    audit=AuditEvent.objects.filter(entity='wfh.wfhrequest',entity_id=str(row['id']),action='update').first()
    assert audit.before['status']=='Pending' and audit.after['status']=='Approved'
    assert audit.actor_id==sample['admin'].pk
