from .settings import *

# ====================================================
#  SUBSCRIBER DATABASE CONFIG (FOR WINDOWS HOST)
# ====================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'myproject',
        'USER': 'myprojectuser',
        'PASSWORD': 'myproject@123',
        'HOST': 'localhost',   # NOT docker 'db'
        'PORT': '5433',        # mapped port
    }
}

# If Celery tries to load anything, disable it
CELERY_BROKER_URL = None
CELERY_RESULT_BACKEND = None
