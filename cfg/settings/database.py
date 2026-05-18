from pathlib import Path

from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATABASES_CONFIG = {
    "postgres": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="127.0.0.1"),
        "PORT": config("DB_PORT", default=5432, cast=int),
        "OPTIONS": {"options": "-c search_path=django,public"},
    },
    "sqlite": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
}
