"""Settings environment production."""

from decouple import Csv, config

from cfg.settings.base import *  # noqa: F403

# ------------------------------------------------------------------------------
#  SECURITY
# ------------------------------------------------------------------------------
DEBUG = False
SECRET_KEY = config("SECRET_KEY")
ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv())

# CORS
CORS_ALLOWED_ORIGINS = config("CORS_ALLOWED_ORIGINS", cast=Csv())
CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", cast=Csv())

# ------------------------------------------------------------------------------
#  MIDDLEWARE
# ------------------------------------------------------------------------------
MIDDLEWARE = list(BASE_MIDDLEWARE)
MIDDLEWARE.insert(0, "corsheaders.middleware.CorsMiddleware")

# ------------------------------------------------------------------------------
#  SECURITY COOKIES & HEADERS (HSTS/SSL)
# ------------------------------------------------------------------------------
# Cookies
CSRF_COOKIE_SECURE = config("CSRF_COOKIE_SECURE", default=True, cast=bool)
CSRF_COOKIE_HTTPONLY = config("CSRF_COOKIE_HTTPONLY", default=True, cast=bool)
CSRF_COOKIE_SAMESITE = "Strict"

SESSION_COOKIE_SECURE = config("SESSION_COOKIE_SECURE", default=True, cast=bool)
SESSION_COOKIE_HTTPONLY = config("SESSION_COOKIE_HTTPONLY", default=True, cast=bool)
SESSION_COOKIE_SAMESITE = "Strict"

# SSL / HSTS
SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", default=31536000, cast=int)  # 1 año
SECURE_HSTS_INCLUDE_SUBDOMAINS = config("SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True, cast=bool)
SECURE_HSTS_PRELOAD = config("SECURE_HSTS_PRELOAD", default=True, cast=bool)

# Security headers
SECURE_CONTENT_TYPE_NOSNIFF = config("SECURE_CONTENT_TYPE_NOSNIFF", default=True, cast=bool)
SECURE_BROWSER_XSS_FILTER = config("SECURE_BROWSER_XSS_FILTER", default=True, cast=bool)
X_FRAME_OPTIONS = config("X_FRAME_OPTIONS", default="DENY")

# Redirection HTTPS
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ------------------------------------------------------------------------------
# REDIS & CELERY CONFIG
# ------------------------------------------------------------------------------
REDIS_HOST = config("REDIS_HOST", default="redis")
REDIS_PORT = config("REDIS_PORT", default=6379, cast=int)
REDIS_DB = config("REDIS_DB", default=0, cast=int)

REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)

CELERY_TIMEZONE = TIME_ZONE
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_EVENT_SERIALIZER = "json"
CELERY_TRANSPORT_OPTIONS = {
    "visibility_timeout": 3600,
    "max_connections": 10,
}

# Task
CELERY_TASK_DEFAULT_QUEUE = "default"
CELERY_TASK_QUEUES = {
    "default": {"exchange": "default", "routing_key": "default"},
    "high_priority": {"exchange": "high_priority", "routing_key": "high_priority"},
    "low_priority": {"exchange": "low_priority", "routing_key": "low_priority"},
}

# ------------------------------------------------------------------------------
# EMAIL CONFIG
# ------------------------------------------------------------------------------
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")

EMAIL_HOST = config("EMAIL_HOST")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)

EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")

DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="COES <no-reply@coes.com>")
SERVER_EMAIL = config("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
