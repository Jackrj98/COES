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
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_HTTPONLY = config("CSRF_COOKIE_HTTPONLY", default=True, cast=bool)
SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
SESSION_COOKIE_HTTPONLY = config("SESSION_COOKIE_HTTPONLY", default=True, cast=bool)
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
REDIS_HOST = config("REDIS_HOST", default="redis")
REDIS_PORT = config("REDIS_PORT", default=6379, cast=int)
CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
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
