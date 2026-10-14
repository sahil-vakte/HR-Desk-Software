import os
import base64
os.environ["DJANGO_ENV"] = "test"
os.environ["DJANGO_SECRET_KEY"] = "test-only-key-not-for-deployment-012345678901234567890123456789"
os.environ["FIELD_ENCRYPTION_KEY"] = base64.urlsafe_b64encode(b"0" * 32).decode()
from .settings import *  # noqa: F403,E402
ALLOWED_HOSTS = ["testserver", "localhost"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
