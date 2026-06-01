from django_app.settings import *
import os

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", get_random_secret_key())

DEBUG = False
ALLOWED_HOSTS = [
    host.strip()
    for host in os.environ.get(
        "DJANGO_ALLOWED_HOSTS",
        "127.0.0.1,localhost,142.93.128.96",
    ).split(",")
    if host.strip()
]

DENTIST_TELEGRAM_BOT_ID = os.environ.get("DENTIST_TELEGRAM_BOT_ID", "")
DENTIST_SHEET_ID = os.environ.get("DENTIST_SHEET_ID", "")
DELIVERY_TELEGRAM_BOT_ID = os.environ.get("DELIVERY_TELEGRAM_BOT_ID", "")
DELIVERY_SHEET_ID = os.environ.get("DELIVERY_SHEET_ID", "")
TERRA_MOTORS_SHEET_ID = os.environ.get("TERRA_MOTORS_SHEET_ID", "")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "/data/django_app.db",
    }
}

STATIC_ROOT = "/static"
STATIC_URL = "/static/"
MEDIA_ROOT = "/data/media"
MEDIA_URL = "/media/"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "[%(asctime)s] %(levelname)s: %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
        "file": {
            "class": "logging.handlers.TimedRotatingFileHandler",
            "filename": "/logs/django_app.log",
            "when": "midnight",
            "backupCount": 60,
            "formatter": "default",
        },
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO",
    },
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": "/data/cache",
    },
}

CELERY_BROKER_URL = "redis://redis:6379"
CELERY_RESULT_BACKEND = "redis://redis:6379"
CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "Asia/Almaty"
