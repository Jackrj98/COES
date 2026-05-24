"""Settings environment production."""

from decouple import Csv, config

from cfg.settings.base import *  # noqa: F403

# ------------------------------------------------------------------------------
#  SECURITY
# ------------------------------------------------------------------------------
DEBUG = False
SECRET_KEY = config("SECRET_KEY")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", cast=Csv())

# ------------------------------------------------------------------------------
#  MIDDLEWARE
# ------------------------------------------------------------------------------
MIDDLEWARE = list(BASE_MIDDLEWARE)
MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")

# ------------------------------------------------------------------------------
#  SECURITY COOKIES & HEADERS (HSTS/SSL)
# ------------------------------------------------------------------------------
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Strict"

SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_HSTS_SECONDS = 31536000  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# ------------------------------------------------------------------------------
# REDIS & CELERY CONFIG
# ------------------------------------------------------------------------------
CELERY_BROKER_URL = config("CELERY_BROKER")
CELERY_RESULT_BACKEND = config("CELERY_BACKEND")
CELERY_EVENT_SERIALIZER = "json"
CELERY_TRANSPORT_OPTIONS = {"visibility_timeout": 3600}

# ------------------------------------------------------------------------------
# EMAIL CONFIG
# ------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="COES <no-reply@coes.com>")

# --- CORS ---
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", cast=Csv())
