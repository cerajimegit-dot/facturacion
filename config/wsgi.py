"""WSGI config for facturacion project."""
import os
from django.core.wsgi import get_wsgi_application

# Forzar settings de produccion en Vercel
os.environ['DJANGO_SETTINGS_MODULE'] = os.environ.get(
    'DJANGO_SETTINGS_MODULE', 'config.settings_prod'
)
application = get_wsgi_application()

# Vercel busca una variable llamada 'app'
app = application
