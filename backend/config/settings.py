from pathlib import Path
import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env", overwrite=False)
ENVIRONMENT = env("DJANGO_ENV", default="production")
if ENVIRONMENT not in {"development", "production", "test"}:
    raise ImproperlyConfigured("DJANGO_ENV must be development, production or test.")
DEBUG = ENVIRONMENT == "development"
SECRET_KEY = env("DJANGO_SECRET_KEY")
if not SECRET_KEY or SECRET_KEY.startswith("replace-"):
    raise ImproperlyConfigured("Generate DJANGO_SECRET_KEY before starting.")
if ENVIRONMENT == "production" and len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("Production secret must be at least 50 characters.")
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
if ENVIRONMENT == "production" and (not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS):
    raise ImproperlyConfigured("Production requires explicit allowed hosts.")
INSTALLED_APPS = [
    "django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions",
    "django.contrib.messages", "django.contrib.staticfiles", "rest_framework", "django_filters",
] + [f"apps.{name}" for name in (
    "accounts", "core", "masters", "employees", "attendance", "leave", "wfh",
    "holidays", "documents", "projects", "pmo", "timesheets", "reports", "recruitment",
)]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.core.middleware.RequestMetadataMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
if DEBUG:
    INSTALLED_APPS.append("corsheaders")
    MIDDLEWARE.insert(1, "corsheaders.middleware.CorsMiddleware")
    CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ALLOWED_ORIGINS", default=[])
    CORS_ALLOW_CREDENTIALS = True
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "APP_DIRS": True,
              "OPTIONS": {"context_processors": ["django.template.context_processors.request",
                  "django.contrib.auth.context_processors.auth",
                  "django.contrib.messages.context_processors.messages"]}}]
DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    db_path = Path(DATABASES["default"]["NAME"])
    if not db_path.is_absolute():
        DATABASES["default"]["NAME"] = BASE_DIR / db_path
    DATABASES["default"]["OPTIONS"] = {"timeout": 20, "transaction_mode": "IMMEDIATE"}
AUTH_USER_MODEL = "accounts.User"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher",
                   "django.contrib.auth.hashers.PBKDF2PasswordHasher"]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = ENVIRONMENT == "production"
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 1800
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = ENVIRONMENT == "production"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
CSRF_FAILURE_VIEW = "apps.core.errors.csrf_failure"
SECURE_SSL_REDIRECT = env.bool(
    "SECURE_SSL_REDIRECT",
    default=ENVIRONMENT == "production",
)
SECURE_HSTS_SECONDS = 31536000 if ENVIRONMENT == "production" else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = ENVIRONMENT == "production"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
USE_TZ = True
TIME_ZONE = "UTC"
LANGUAGE_CODE = "en-gb"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
_media = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "private_media")))
MEDIA_ROOT = (_media if _media.is_absolute() else BASE_DIR / _media).resolve()
if MEDIA_ROOT == STATIC_ROOT.resolve() or STATIC_ROOT.resolve() in MEDIA_ROOT.parents:
    raise ImproperlyConfigured("MEDIA_ROOT must be outside the public static root.")
# Deliberately no URL mapping to MEDIA_ROOT.
FILE_UPLOAD_PERMISSIONS = 0o600
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o700
DATA_UPLOAD_MAX_MEMORY_SIZE = 11 * 1024 * 1024
EMAIL_BACKEND = env("EMAIL_BACKEND", default=("django.core.mail.backends.console.EmailBackend"
                    if DEBUG else "django.core.mail.backends.smtp.EmailBackend"))
EMAIL_HOST = env("EMAIL_HOST", default="localhost")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
if EMAIL_USE_TLS and EMAIL_USE_SSL:
    raise ImproperlyConfigured("Enable only one of EMAIL_USE_TLS or EMAIL_USE_SSL.")
EMAIL_TIMEOUT = 20
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="hrdesk@example.invalid")
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.core.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["apps.core.permissions.DenyUnconfiguredEndpoint"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "apps.core.errors.exception_handler",
    "DATE_FORMAT": "%Y-%m-%d",
}
LOGGING = {"version": 1, "disable_existing_loggers": False,
           "handlers": {"console": {"class": "logging.StreamHandler"}},
           "loggers": {"hrdesk": {"handlers": ["console"], "level": "INFO", "propagate": False}}}

AUTHENTICATION_BACKENDS = ["apps.accounts.authentication.EmailBackend"]
AUTH_PASSWORD_VALIDATORS.append({"NAME": "apps.core.validators.StrongPasswordValidator"})
MIDDLEWARE.insert(MIDDLEWARE.index("django.contrib.auth.middleware.AuthenticationMiddleware")+1,
                  "apps.accounts.middleware.SessionLifetimeMiddleware")
FIELD_ENCRYPTION_KEY = env("FIELD_ENCRYPTION_KEY")
from cryptography.fernet import Fernet
try:
    Fernet(FIELD_ENCRYPTION_KEY.encode())
except (ValueError, TypeError):
    raise ImproperlyConfigured("FIELD_ENCRYPTION_KEY must be a valid Fernet key; run scripts/init_env.py.")
FRONTEND_ORIGIN = env("FRONTEND_ORIGIN", default="http://localhost:3000")

STATICFILES_DIRS = [BASE_DIR.parent / "frontend" / "build" / "static"] if (BASE_DIR.parent / "frontend" / "build" / "static").exists() else []
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
# Render terminates HTTPS at its proxy and forwards the original
# protocol to the Django application.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
