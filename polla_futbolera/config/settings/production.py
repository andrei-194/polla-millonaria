from .base import *
from decouple import config
import urllib.parse as _up

DEBUG = False

# RAILWAY_PUBLIC_DOMAIN es inyectada automáticamente por Railway con el dominio real del servicio.
# ALLOWED_HOSTS en el panel se usa solo para dominios custom adicionales.
_railway_public = config("RAILWAY_PUBLIC_DOMAIN", default="")
_extra = config("ALLOWED_HOSTS", default="localhost,127.0.0.1")
ALLOWED_HOSTS = [h.strip() for h in _extra.split(",") if h.strip()]
if _railway_public and _railway_public not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(_railway_public)

# CUSTOM_DOMAIN permite declarar el dominio propio sin tocar ALLOWED_HOSTS/CSRF a mano.
# Agregar en Railway Variables: CUSTOM_DOMAIN=toquela.com
_custom_domain = config("CUSTOM_DOMAIN", default="")
if _custom_domain:
    for _host in [_custom_domain, f"www.{_custom_domain}"]:
        if _host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_host)

_csrf_origins = config("CSRF_TRUSTED_ORIGINS", default="")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(",") if o.strip()]
if _railway_public:
    _railway_origin = f"https://{_railway_public}"
    if _railway_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_railway_origin)
if _custom_domain:
    for _origin in [f"https://{_custom_domain}", f"https://www.{_custom_domain}"]:
        if _origin not in CSRF_TRUSTED_ORIGINS:
            CSRF_TRUSTED_ORIGINS.append(_origin)

_database_url = config("DATABASE_URL")
_parsed = _up.urlparse(_database_url)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _parsed.path.lstrip("/"),
        "USER": _parsed.username,
        "PASSWORD": _parsed.password,
        "HOST": _parsed.hostname,
        "PORT": str(_parsed.port or 5432),
    }
}

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = False  # Railway termina HTTPS en el proxy; el contenedor recibe HTTP
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

EMAIL_BACKEND = "anymail.backends.resend.EmailBackend"
ANYMAIL = {"RESEND_API_KEY": config("RESEND_API_KEY", default="")}
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="onboarding@resend.dev")

import sentry_sdk
_sentry_dsn = config("SENTRY_DSN", default="")
if _sentry_dsn:
    sentry_sdk.init(dsn=_sentry_dsn, traces_sample_rate=0.1)
