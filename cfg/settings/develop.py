"""Settings environment development."""

from decouple import config

from cfg.settings.base import *  # noqa: F403

# ------------------------------------------------------------------------------
# SECURITY
# ------------------------------------------------------------------------------
DEBUG = True
SECRET_KEY = config("SECRET_KEY", default="django-insecure-dev-key-static")
ALLOWED_HOSTS = ["*"]

INTERNAL_IPS = ["127.0.0.1", "localhost", "0.0.0.0", "172.19.0.4", "*"]

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

CELERY_BROKER_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = CELERY_BROKER_URL

CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = TIME_ZONE

# ------------------------------------------------------------------------------
# EMAIL CONFIG
# ------------------------------------------------------------------------------
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")
EMAIL_HOST = config("TS_EMAIL_HOST", default="localhost")
EMAIL_PORT = config("TS_EMAIL_PORT", default=1025, cast=int)
EMAIL_USE_TLS = config("TS_EMAIL_TLS", default=False, cast=bool)
EMAIL_USE_SSL = config("TS_EMAIL_SSL", default=False, cast=bool)
EMAIL_HOST_USER = config("TS_EMAIL_USER", default="")
EMAIL_HOST_PASSWORD = config("TS_EMAIL_PASSWORD", default="")
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="no-reply@coes.com")

# ------------------------------------------------------------------------------
# DEBUG TOOLBAR
# ------------------------------------------------------------------------------
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
    "IS_RUNNING_TESTS": False,
}
