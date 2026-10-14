import json
from io import StringIO
from pathlib import Path
import pytest
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, models
from django.http import JsonResponse
from django.test import Client, RequestFactory, override_settings
from django.views.decorators.csrf import csrf_protect
from rest_framework.exceptions import ValidationError as ApiValidationError
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView
from apps.core.errors import exception_handler
from apps.core.models import AuditEvent, BaseModel
from apps.core.pagination import StandardPagination


def test_health_minimal_and_no_state_change():
    client = Client()
    response = client.get('/api/v1/health/')
    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}
    assert 'sessionid' not in response.cookies
    assert client.post('/api/v1/health/').status_code == 405


def test_csrf_cookie_is_http_only():
    response = Client().get('/api/v1/auth/csrf/')
    assert response.status_code == 200
    assert response.cookies['csrftoken']['httponly']
    assert response.cookies['csrftoken']['samesite'] == 'Lax'
    assert response.json()['csrfToken']
    assert 'no-store' in response['Cache-Control']


def test_anonymous_unsafe_view_requires_csrf():
    @csrf_protect
    def unsafe(request):
        return JsonResponse({'ok': True})
    request = RequestFactory().post('/probe/')
    response = unsafe(request)
    assert response.status_code == 403
    assert json.loads(response.content)['errors'] == {}


def test_validation_errors_are_422():
    response = exception_handler(ApiValidationError({'name': ['Required.']}), {})
    assert response.status_code == 422
    assert response.data == {'message': 'The given data was invalid.', 'errors': {'name': ['Required.']}}


def test_unknown_error_redacts_sensitive_message():
    response = exception_handler(RuntimeError('private bank account'), {})
    assert response.status_code == 500
    assert 'private' not in json.dumps(response.data)


def test_unconfigured_endpoint_fails_closed():
    response = APIView.as_view()(APIRequestFactory().get('/probe/'))
    assert response.status_code == 401
    assert response.data['message'] == 'Authentication required.'


def test_authenticated_unconfigured_endpoint_denies_access():
    from rest_framework.test import force_authenticate
    request = APIRequestFactory().get('/probe/')
    force_authenticate(request, user=type('Principal', (), {'is_authenticated': True})())
    response = APIView.as_view()(request)
    assert response.status_code == 403


def test_pagination_shape_and_limit():
    from rest_framework.request import Request
    request = Request(APIRequestFactory().get('/probe/?page_size=10000'))
    paginator = StandardPagination()
    page = paginator.paginate_queryset(list(range(205)), request)
    assert len(page) == 100
    assert set(paginator.get_paginated_response(page).data) == {'count', 'next', 'previous', 'results'}


def test_unknown_and_media_urls_are_not_public():
    client = Client()
    for url in ['/api/v1/missing/', '/media/passport.pdf', '/private_media/passport.pdf']:
        response = client.get(url)
        assert response.status_code == 404
        assert response.json() == {'message': 'Record not found.', 'errors': {}}


@pytest.mark.django_db
def test_seed_check_matches_authoritative_ids():
    output = StringIO()
    call_command('seed', '--check', stdout=output)
    assert '75 unique' in output.getvalue()
    call_command("seed", stdout=output)
    from apps.accounts.models import MenuItem
    assert MenuItem.objects.count() == 75


@pytest.mark.django_db
def test_audit_events_are_append_only():
    event = AuditEvent.objects.create(entity='probe', entity_id='1', action='create')
    event.action = 'changed'
    with pytest.raises(ValidationError):
        event.save()
    with pytest.raises(ValidationError):
        event.delete()
    with pytest.raises(ValidationError):
        AuditEvent.objects.update(action='changed')
    with pytest.raises(ValidationError):
        AuditEvent.objects.all().delete()


@pytest.mark.django_db(transaction=True)
def test_sqlite_foreign_keys_enabled():
    with connection.cursor() as cursor:
        cursor.execute('PRAGMA foreign_keys;')
        assert cursor.fetchone()[0] == 1


class Probe(BaseModel):
    name = models.CharField(max_length=20, unique=True)
    audit_fields = ('name', 'status', 'is_deleted')
    class Meta(BaseModel.Meta):
        app_label = 'core'


@pytest.fixture
def probe_table(transactional_db):
    with connection.schema_editor() as editor:
        editor.create_model(Probe)
    yield
    with connection.schema_editor() as editor:
        editor.delete_model(Probe)


def test_soft_delete_and_mutations_are_audited(probe_table):
    row = Probe(name='Fictional')
    row.save()
    row.status = False
    row.save()
    row.delete()
    assert not Probe.objects.filter(pk=row.pk).exists()
    assert Probe.all_objects.get(pk=row.pk).is_deleted
    assert list(AuditEvent.objects.order_by('pk').values_list('action', flat=True)) == ['create', 'update', 'delete']
    assert row.delete() == (0, {})


def test_delete_constraint_and_bulk_write_guards(probe_table):
    with pytest.raises(IntegrityError):
        Probe(name='Invalid', is_deleted=True).save()
    assert AuditEvent.objects.count() == 0
    with pytest.raises(ValidationError):
        Probe.objects.bulk_create([Probe(name='Bulk')])
    with pytest.raises(ValidationError):
        Probe.objects.update(status=False)


def test_audit_failure_rolls_back_mutation(probe_table, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError('audit unavailable')
    monkeypatch.setattr(AuditEvent.objects, 'create', fail)
    with pytest.raises(RuntimeError):
        Probe(name='Rollback').save()
    assert Probe.all_objects.count() == 0


@override_settings(ENVIRONMENT='production', SECURE_SSL_REDIRECT=True,
                   SECURE_HSTS_SECONDS=31536000, SECURE_HSTS_INCLUDE_SUBDOMAINS=True)
def test_https_and_headers():
    client = Client()
    assert client.get('/api/v1/health/').status_code == 301
    response = client.get('/api/v1/health/', secure=True)
    assert response['X-Frame-Options'] == 'DENY'
    assert response['X-Content-Type-Options'] == 'nosniff'
    assert "default-src 'self'" in response['Content-Security-Policy']
    assert '31536000' in response['Strict-Transport-Security']


def test_session_security_configuration():
    assert settings.SESSION_COOKIE_HTTPONLY
    assert settings.SESSION_COOKIE_SAMESITE == 'Lax'
    assert settings.SESSION_COOKIE_AGE == 1800
    assert settings.CSRF_COOKIE_HTTPONLY
