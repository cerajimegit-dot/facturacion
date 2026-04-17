"""Production settings for Vercel + Supabase deployment."""
from .settings import *

import os
import dj_database_url

# Database Configuration
DATABASES = {
    'default': dj_database_url.parse(os.environ.get('SUPABASE_URL', 'sqlite:///db.sqlite3'))
}
# Asegurar search_path y encoding para Supabase
if DATABASES['default'].get('ENGINE', '').endswith('postgresql'):
    DATABASES['default'].setdefault('OPTIONS', {})
    DATABASES['default']['OPTIONS']['options'] = '-c search_path=public -c client_encoding=UTF8'

# Security Settings
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = ['*']  # TODO: restringir despues de verificar que funciona
SECRET_KEY = os.environ.get('SECRET_KEY', SECRET_KEY)

# CORS Configuration
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://facturacion-app.vercel.app",
    "https://*.vercel.app",
    "http://localhost:8501",
    "http://127.0.0.1:8501"
]

# Static and Media Files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# WhiteNoise: servir estaticos sin necesidad de manifest
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'

# Supabase Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Session and Security
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_SSL_REDIRECT = False  # Vercel maneja SSL, no redirigir en Django

# Performance
USE_TZ = True
TIME_ZONE = 'America/Asuncion'
