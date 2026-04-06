from pathlib import Path
from datetime import timedelta  # Make sure this import is at the top of your settings.py
import os
import logging
import json
import socket

from decouple import AutoConfig, Csv

BASE_DIR = Path(__file__).resolve().parent.parent
config = AutoConfig(search_path=BASE_DIR)

# SECURITY WARNING: keep the secret key secret!
SECRET_KEY = config("SECRET_KEY")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="", cast=Csv())


# ---------------------------
# INSTALLED APPS
# ---------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third Party
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "drf_yasg",

    # Local Apps
    "blog_app",
    "blog_app.audio.apps.AudioConfig",
    "subscription",
]


# ---------------------------
# MIDDLEWARE
# ---------------------------
MIDDLEWARE = [
    "myproject.middleware.DisableCSRFMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "myproject.urls"


# ---------------------------
# TEMPLATES
# ---------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "myproject.wsgi.application"


# ---------------------------
# DATABASE CONFIG (POSTGRES)
# ---------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST"),
        "PORT": config("DB_PORT", cast=int),
    }
}


# ---------------------------
# AUTH USER MODEL
# ---------------------------
AUTH_USER_MODEL = "blog_app.User"


# ---------------------------
# PASSWORD VALIDATION
# ---------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# JWT SETTINGS
SIMPLE_JWT = {
    # Increase Access Token to 24 hours (1 day)
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),

    # Increase Refresh Token to 7 days
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------
# DRF SETTINGS
# ---------------------------
REST_FRAMEWORK = {
    "DATETIME_FORMAT": "%Y-%m-%dT%H:%M:%S",

    "DATETIME_INPUT_FORMATS": [
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S.%f",
    ],

    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ),

    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
}


# ---------------------------
# TIMEZONE SETTINGS
# ---------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True


# ---------------------------
# STATIC & MEDIA (IMPORTANT)
# ---------------------------

# Static files (CSS/JS/images)
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Media files (uploads like images, docx, pdf - optional)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Create media directory if missing
os.makedirs(MEDIA_ROOT, exist_ok=True)


# ---------------------------
# DEFAULT FIELD
# ---------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ---------------------------
# SWAGGER SETTINGS
# ---------------------------
SWAGGER_SETTINGS = {
    "SECURITY_DEFINITIONS": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "JWT Authorization header: Bearer <token>",
        }
    },
    "USE_SESSION_AUTH": False,
}


# ----------------------------------------------------
# Custom Logstash TCP Handler
# ----------------------------------------------------
class LogstashTCPHandler(logging.Handler):
    def emit(self, record):
        log_entry = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        skip_keys = {
            "name", "msg", "args", "levelname", "levelno",
            "pathname", "filename", "module", "exc_info",
            "exc_text", "stack_info", "lineno", "funcName",
            "created", "msecs", "relativeCreated",
            "thread", "threadName", "processName", "process"
        }

        for key, value in record.__dict__.items():
            if key not in skip_keys:
                log_entry[key] = value

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(("logstash", 5044))   # MUST match docker service name
            sock.sendall((json.dumps(log_entry) + "\n").encode("utf-8"))
            sock.close()
        except Exception as e:
            print("Logstash connection error:", e)


# ----------------------------------------------------
# LOGGING CONFIG
# ----------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "logstash": {
            "()": LogstashTCPHandler,
        },
    },
    "loggers": {
        "blog_publisher": {
            "handlers": ["logstash"],
            "level": "INFO",
            "propagate": False,
        },
    },
}

# ---------------------------
# CELERY CONFIGURATION
# ---------------------------
CELERY_BROKER_URL = config("CELERY_BROKER_URL")
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND")

CELERY_TIMEZONE = "Asia/Kolkata"
CELERY_ENABLE_UTC = False


RAZORPAY_KEY_ID = config("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = config("RAZORPAY_KEY_SECRET")
ANTHROPIC_API_KEY = config("ANTHROPIC_API_KEY", default="")
GROQ_API_KEY = config("GROQ_API_KEY", default="")
