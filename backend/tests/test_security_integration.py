from datetime import timedelta
import io
import hashlib
import pytest
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone
from django.core import mail
from rest_framework.test import APIClient
from apps.accounts.models import User, PasswordReset, RolePermission
from apps.core.models import AuditEvent, PrivateFile
from apps.employees.models import Employee
from apps.masters.models import MasterItem
from tests.test_acceptance import sample, client, PASSWORD, wfh

pytestmark=pytest.mark.django_db

def test_login_requires_csrf_even_before_authentication(sample):
    c=APIClient(enforce_csrf_checks=True)
    r=c.post('/api/v1/auth/login/',{'email':sample['a'].email,'password':PASSWORD},format='json')
    assert r.status_code==403
    assert not AuditEvent.objects.filter(action='login').exists()


def test_session_unsafe_request_requires_csrf(sample):
    c=APIClient(enforce_csrf_checks=True)
    token=c.get('/api/v1/auth/csrf/').data if hasattr(c.get('/api/v1/auth/csrf/'),'data') else None
    token=c.get('/api/v1/auth/csrf/').json()['csrfToken']
    assert c.post('/api/v1/auth/login/',{'email':sample['a'].email,'password':PASSWORD},format='json',HTTP_X_CSRFTOKEN=token).status_code==200
    assert c.post('/api/v1/wfh-requests/',{'duration':'Full Day','date':str(sample['start'])},format='json').status_code==403


def test_absolute_session_expiry(sample):
    c=APIClient();c.post('/api/v1/auth/login/',{'email':sample['a'].email,'password':PASSWORD},format='json')
    session=c.session;session['authenticated_at']=(timezone.now()-timedelta(hours=13)).timestamp();session.save()
    assert c.get('/api/v1/session/').status_code==401


def test_reset_single_use_invalidates_session(sample):
    c=APIClient();c.post('/api/v1/auth/login/',{'email':sample['a'].email,'password':PASSWORD},format='json')
    token='fictional-token';PasswordReset.objects.create(user=sample['a'],digest=hashlib.sha256(token.encode()).hexdigest(),expires_at=timezone.now()+timedelta(minutes=10))
    payload={'token':token,'password':'Replacement-Test-Password8!','confirm_password':'Replacement-Test-Password8!'}
    anon=APIClient()
    assert anon.post('/api/v1/auth/password/reset/',payload,format='json').status_code==200
    assert anon.post('/api/v1/auth/password/reset/',payload,format='json').status_code==422
    assert c.get('/api/v1/session/').status_code==401


def test_seed_does_not_regrant_removed_permissions(sample):
    grant=RolePermission.objects.get(role_id=4,menu_item_id=52);grant.delete(actor=sample['admin'])
    call_command('seed',stdout=io.StringIO())
    assert not RolePermission.objects.filter(role_id=4,menu_item_id=52).exists()


def test_employee_admin_idor(sample):
    e=Employee.objects.get(user=sample['b'])
    r=client(sample['a']).get(f'/api/v1/employees/{e.pk}/')
    assert r.status_code==403
    r=client(sample['a']).get(f'/api/v1/employees/{e.pk}/documents/')
    assert r.status_code==403


def test_file_idor(sample):
    file=PrivateFile(owner=sample['b'],stored_name='fictional.pdf',original_name='fictional.pdf',content_type='application/pdf',size=10,sha256='a'*64,purpose='employee');file.save()
    assert client(sample['a']).get(f'/api/v1/files/{file.pk}/download/').status_code==403


def test_upload_cannot_attach_another_users_private_file(sample):
    file=PrivateFile(owner=sample['b'],stored_name='fictional.pdf',original_name='fictional.pdf',content_type='application/pdf',size=10,sha256='a'*64,purpose='employee');file.save()
    r=client(sample['a']).post('/api/v1/wsr/',{'week_start':str(sample['start']),'attachment':file.pk},format='json')
    assert r.status_code==403


def test_sensitive_employee_values_encrypted(sample):
    from django.db import connection
    e=Employee.objects.get(user=sample['a']);e.medical_condition='Fictional sensitive text';e.save()
    with connection.cursor() as cursor:
        cursor.execute('SELECT medical_condition FROM employees_employee WHERE id=%s',[e.pk]);raw=cursor.fetchone()[0]
    assert 'Fictional sensitive text' not in raw
    e.refresh_from_db();assert e.medical_condition=='Fictional sensitive text'
    assert 'medical_condition' not in client(sample['a']).get('/api/v1/me/profile/').data


def test_admin_cannot_escalate_through_onboarding(sample):
    sample['a'].role_id=2;sample['a'].save()
    r=client(sample['a']).post('/api/v1/employees/onboard/',{'account':{'role':1}},format='json')
    assert r.status_code==403


def test_get_cannot_approve(sample):
    row=wfh(sample)
    assert client(sample['admin']).get(f"/api/v1/wfh-requests/{row['id']}/approve/").status_code==405


def test_active_leave_type_lookup_for_employee(sample):
    r=client(sample['a']).get('/api/v1/lookups/leave.LeaveType/')
    assert r.status_code==200
    assert sample['type'].pk in [x['id'] for x in r.data]


def test_core_resource_metadata_for_all_seeded_roles(sample):
    for role_id in range(1,9):
        sample['a'].role_id=role_id;sample['a'].save()
        r=client(sample['a']).get('/api/v1/ui/resources/')
        assert r.status_code==200,r.data
        assert all('fields' in row for row in r.data)


def test_report_csv_and_pdf(sample):
    c=client(sample['admin'])
    csv=c.get('/api/v1/reports/leave/?export=csv');assert csv.status_code==200
    assert 'text/csv' in csv['Content-Type']
    pdf=c.get('/api/v1/reports/leave/?export=pdf');assert pdf.status_code==200
    assert pdf.content.startswith(b'%PDF')
