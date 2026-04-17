"""WSGI config for facturacion project."""
import os
import subprocess
from django.core.wsgi import get_wsgi_application

# Forzar settings de produccion en Vercel
os.environ['DJANGO_SETTINGS_MODULE'] = os.environ.get(
    'DJANGO_SETTINGS_MODULE', 'config.settings_prod'
)

# Ejecutar collectstatic en el build de Vercel (solo una vez)
_static_root = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'staticfiles')
if not os.path.exists(os.path.join(_static_root, 'staticfiles.json')):
    try:
        subprocess.run(
            ['python', 'manage.py', 'collectstatic', '--noinput',
             '--settings', os.environ['DJANGO_SETTINGS_MODULE']],
            check=True, capture_output=True
        )
    except Exception:
        pass  # No fallar si collectstatic no funciona

application = get_wsgi_application()

# Vercel busca una variable llamada 'app'
app = application
