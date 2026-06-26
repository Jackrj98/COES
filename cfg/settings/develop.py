"""Settings environment development."""

from decouple import Csv, config

from cfg.settings.base import *  # noqa: F403

# ------------------------------------------------------------------------------
# SECURITY
# ------------------------------------------------------------------------------
DEBUG = True
SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-key-static")

ALLOWED_HOSTS = config("ALLOWED_HOSTS", cast=Csv(), default=["*"])
INTERNAL_IPS = config("ALLOWED_HOSTS", cast=Csv(), default=["*"])

# ------------------------------------------------------------------------------
# APP DEFINITION
# ------------------------------------------------------------------------------
INSTALLED_APPS += ["debug_toolbar", "django_seed"]

# ------------------------------------------------------------------------------
# MIDDLEWARE
# ------------------------------------------------------------------------------
MIDDLEWARE = list(MIDDLEWARE)
if "debug_toolbar.middleware.DebugToolbarMiddleware" not in MIDDLEWARE:
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")

# ------------------------------------------------------------------------------
# REDIS & CELERY CONFIG
# ------------------------------------------------------------------------------
REDIS_HOST = config("REDIS_HOST", default="redis")
REDIS_PORT = config("REDIS_PORT", default=6379, cast=int)

REDIS_URL = config("REDIS_URL", default=f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)

CELERY_TASK_SERIALIZER = config("CELERY_TASK_SERIALIZER", default="json")
CELERY_RESULT_SERIALIZER = config("CELERY_RESULT_SERIALIZER", default="json")
CELERY_ACCEPT_CONTENT = config("CELERY_ACCEPT_CONTENT", default="json")
CELERY_ACCEPT_CONTENT = [content.strip() for content in CELERY_ACCEPT_CONTENT.split(",")]
CELERY_TIMEZONE = config("CELERY_TIMEZONE", default=TIME_ZONE)


# ------------------------------------------------------------------------------
# EMAIL CONFIG
# ------------------------------------------------------------------------------
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("EMAIL_HOST", default="mailhog")
EMAIL_PORT = config("EMAIL_PORT", default=1025, cast=int)
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
SERVER_EMAIL = config("SERVER_EMAIL", default="no-reply@coes.com")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default=SERVER_EMAIL)

# ------------------------------------------------------------------------------
# DEBUG TOOLBAR
# ------------------------------------------------------------------------------
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
    "IS_RUNNING_TESTS": False,
}
