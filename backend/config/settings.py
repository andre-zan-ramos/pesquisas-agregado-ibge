import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)


def positive_int(name, default):
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} deve ser inteiro positivo.") from exc
    if value <= 0:
        raise ImproperlyConfigured(f"{name} deve ser inteiro positivo.")
    return value


DEBUG = os.getenv("DJANGO_DEBUG", "false").lower() == "true"
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")
if not SECRET_KEY:
    raise ImproperlyConfigured("Configure DJANGO_SECRET_KEY em backend/.env ou no ambiente.")
ALLOWED_HOSTS = [s.strip() for s in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if s.strip()]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
INSTALLED_APPS = ["rest_framework", "agregados"]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
# Sem modelos, autenticação ou banco nesta fase.
DATABASES = {"default": {"ENGINE": "django.db.backends.dummy"}}
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "agregados.errors.exception_handler",
}
CACHES = {"default": {
    "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    "LOCATION": "agregados-ibge",
    "OPTIONS": {"MAX_ENTRIES": 64},
}}
IBGE_CONNECT_TIMEOUT = positive_int("IBGE_CONNECT_TIMEOUT", 5)
IBGE_READ_TIMEOUT = positive_int("IBGE_READ_TIMEOUT", 15)
IBGE_TOTAL_TIMEOUT = positive_int("IBGE_TOTAL_TIMEOUT", 25)
IBGE_MAX_ATTEMPTS = positive_int("IBGE_MAX_ATTEMPTS", 2)
if IBGE_MAX_ATTEMPTS > 3:
    raise ImproperlyConfigured("IBGE_MAX_ATTEMPTS não pode exceder 3.")
IBGE_MAX_RESPONSE_BYTES = positive_int("IBGE_MAX_RESPONSE_BYTES", 4 * 1024 * 1024)
IBGE_MAX_CONCURRENT = positive_int("IBGE_MAX_CONCURRENT", 2)
IBGE_CATALOG_TTL = positive_int("IBGE_CATALOG_TTL", 3600)
IBGE_SERIES_TTL = positive_int("IBGE_SERIES_TTL", 300)
IBGE_MAX_VARIABLES = positive_int("IBGE_MAX_VARIABLES", 6)
IBGE_MAX_LOCALITIES = positive_int("IBGE_MAX_LOCALITIES", 5)
IBGE_MAX_OBSERVATIONS = positive_int("IBGE_MAX_OBSERVATIONS", 10000)
