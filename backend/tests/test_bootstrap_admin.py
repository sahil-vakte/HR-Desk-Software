import pytest
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from apps.accounts.models import Role, User
from apps.core.models import AuditEvent

pytestmark = pytest.mark.django_db
URL = '/api/v1/auth/bootstrap-admin/'
TOKEN = 'test-only-bootstrap-token'
PASSWORD = 'Testing-Administrator-962!'


@pytest.fixture(autouse=True)
def bootstrap_settings(settings):
    settings.BOOTSTRAP_ADMIN_ENABLED = True
    settings.BOOTSTRAP_ADMIN_TOKEN = TOKEN
    settings.ENVIRONMENT = 'test'
    cache.clear()
    Role.objects.create(pk=1, title='Administrator', slug='administrator')


def payload(**changes):
    return dict(email='NewAdmin@example.invalid', first_name='New', last_name='Administrator',
                password=PASSWORD, confirm_password=PASSWORD, **changes)


def post(client=None, data=None, token=TOKEN, **headers):
    return (client or APIClient()).post(URL, data or payload(), format='json',
                                        HTTP_X_BOOTSTRAP_TOKEN=token, **headers)


def test_create_audited_admin_then_login():
    assert post().status_code == 201
    user = User.objects.get(email='newadmin@example.invalid')
    assert user.is_staff and user.is_superuser and user.role_id == 1
    assert user.check_password(PASSWORD)
    assert AuditEvent.objects.filter(actor=user, action='administrator_created').exists()
    assert APIClient().post('/api/v1/auth/login/', {'email': user.email, 'password': PASSWORD},
                            format='json').status_code == 200


@pytest.mark.parametrize('environment', ['test', 'production'])
def test_disabled_flag_blocks_all_environments(environment):
    with override_settings(BOOTSTRAP_ADMIN_ENABLED=False, ENVIRONMENT=environment):
        assert post().status_code == 404
    assert not User.objects.exists()


def test_enabled_in_production_mode():
    with override_settings(ENVIRONMENT='production', BOOTSTRAP_ADMIN_ENABLED=True):
        assert post().status_code == 201
    assert User.objects.get(email='newadmin@example.invalid').is_superuser


@pytest.mark.parametrize('token', ['', 'incorrect'])
def test_token_required(token):
    assert post(token=token).status_code == 403
    assert not User.objects.exists()


def test_csrf_required_and_valid_token_accepted():
    client = APIClient(enforce_csrf_checks=True)
    assert post(client).status_code == 403
    csrf = client.get('/api/v1/auth/csrf/').json()['csrfToken']
    assert post(client, HTTP_X_CSRFTOKEN=csrf).status_code == 201


def test_weak_password_and_duplicate_email_rejected():
    data = payload(); data.update(password='weak', confirm_password='weak')
    assert post(data=data).status_code == 422
    assert not User.objects.exists()
    assert post().status_code == 201
    assert post().status_code == 422
    assert User.objects.count() == 1


def test_rate_limit_failed_token_attempts():
    for _ in range(5):
        assert post(token='incorrect').status_code == 403
    assert post().status_code == 429
    assert not User.objects.exists()
