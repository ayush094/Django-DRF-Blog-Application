from pathlib import Path
from datetime import timedelta  # Make sure this import is at the top of your settings.py
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key secret!
SECRET_KEY = "django-insecure-w4&c_o8)n8*-syk3x3_u+)&rpuo7+7f&w)5id(*@otk0=(n19+"

DEBUG = True

ALLOWED_HOSTS = ["*"]


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
        "NAME": "myproject",
        "USER": "myprojectuser",
        "PASSWORD": "myproject@123",
        "HOST": "db",
        "PORT": "5432",
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

# Media files (uploads like images, docx, pdf — optional)
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


# ---------------------------
# CELERY CONFIGURATION
# ---------------------------
CELERY_BROKER_URL = "redis://redis:6379/0"
CELERY_RESULT_BACKEND = "redis://redis:6379/0"

CELERY_TIMEZONE = "Asia/Kolkata"
CELERY_ENABLE_UTC = False



RAZORPAY_KEY_ID = "rzp_test_RtNmiEOX0YojZG"
RAZORPAY_KEY_SECRET = "eJfXq0ynpHh0PyhxKYQlNj5B"

