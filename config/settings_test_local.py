"""Test settings for local development with SQLite."""
from .settings import *

# Use SQLite for local testing
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_facturacion.db',
    }
}

# Override database URL if set
import os
if os.environ.get('DATABASE_URL'):
    import dj_database_url
    DATABASES['default'] = dj_database_url.parse(os.environ.get('DATABASE_URL'))

# Debug mode for testing
DEBUG = True
ALLOWED_HOSTS = ['*']

# CORS for testing
CORS_ALLOW_ALL_ORIGINS = True

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Media files for testing
MEDIA_ROOT = BASE_DIR / 'test_media'
STATIC_ROOT = BASE_DIR / 'test_static'

# Disable celery for testing
CELERY_BROKER_URL = None
CELERY_RESULT_BACKEND = None
