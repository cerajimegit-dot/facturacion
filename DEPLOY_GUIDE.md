# 🚀 Guía de Despliegue - Vercel + Supabase

## 📋 Arquitectura de Deploy

### Frontend (Vercel)
- **Platform**: Vercel
- **Framework**: Streamlit
- **URL**: https://facturacion-app.vercel.app
- **Environment Variables**: Configuradas en Vercel

### Backend (Vercel Functions)
- **Platform**: Vercel Functions (Serverless)
- **Framework**: Django REST API
- **Database**: Supabase PostgreSQL
- **URL**: https://facturacion-api.vercel.app

### Database (Supabase)
- **Platform**: Supabase
- **Service**: PostgreSQL
- **Features**: Auth, Storage, Edge Functions

---

## 🔧 Paso 1: Configurar Supabase

### 1.1 Crear Proyecto Supabase
```bash
# Ir a https://supabase.com
# 1. Sign up / Login
# 2. Click "New Project"
# 3. Organization: Tu org
# 4. Project Name: facturacion-app
# 5. Database Password: Generar segura
# 6. Region: South America (Brazil)
# 7. Click "Create new project"
```

### 1.2 Configurar Database
```sql
-- Una vez creado el proyecto, ir a SQL Editor
-- Ejecutar migraciones iniciales

-- Crear extensiones necesarias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Configurar timezone
SET timezone = 'America/Asuncion';
```

### 1.3 Obtener Credenciales
```bash
# En Supabase Dashboard:
# Project Settings > API
# Copiar:
# - Project URL (SUPABASE_URL)
# - anon public key (SUPABASE_ANON_KEY)
# - service_role key (SUPABASE_SERVICE_KEY)
```

---

## 🔧 Paso 2: Adaptar Backend para Vercel

### 2.1 Crear `vercel.json`
```json
{
  "version": 2,
  "builds": [
    {
      "src": "manage.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/api/(.*)",
      "dest": "/manage.py"
    },
    {
      "src": "/(.*)",
      "dest": "/manage.py"
    }
  ],
  "env": {
    "DJANGO_SETTINGS_MODULE": "config.settings_prod"
  }
}
```

### 2.2 Crear `config/settings_prod.py`
```python
from .settings import *

# Production settings for Vercel
import os
import dj_database_url
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

# Database
DATABASES = {
    'default': dj_database_url.parse(os.environ.get('SUPABASE_URL'))
}

# Security
DEBUG = False
ALLOWED_HOSTS = ['*.vercel.app', 'localhost', '127.0.0.1']
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# CORS
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = [
    "https://facturacion-app.vercel.app",
    "https://*.vercel.app"
]

# Static files
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATIC_URL = '/static/'

# Media files
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Supabase
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_ANON_KEY = os.environ.get('SUPABASE_ANON_KEY')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

# Sentry (optional)
SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True
    )
```

### 2.3 Crear `api/index.py` (Vercel Functions)
```python
import os
import sys
import django
from django.core.wsgi import get_wsgi_application
from django.http import JsonResponse

# Add project to path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_prod')
django.setup()

# Get WSGI application
application = get_wsgi_application()

# Vercel serverless handler
def handler(request):
    return application(request)
```

### 2.4 Actualizar `requirements.txt`
```txt
# Core
Django==4.2.7
djangorestframework==3.14.0
djangorestframework-simplejwt==5.3.0
drf-spectacular==0.26.5

# Database
psycopg2-binary==2.9.7
dj-database-url==2.1.0

# Vercel/Production
gunicorn==21.2.0
whitenoise==6.6.0

# Monitoring (optional)
sentry-sdk==1.38.0

# Existing dependencies
...
```

---

## 🔧 Paso 3: Adaptar Frontend para Vercel

### 3.1 Crear `vercel.json` para frontend
```json
{
  "version": 2,
  "builds": [
    {
      "src": "app.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "/app.py"
    }
  ],
  "env": {
    "STREAMLIT_SERVER_PORT": "8080",
    "STREAMLIT_SERVER_ADDRESS": "0.0.0.0"
  }
}
```

### 3.2 Crear `api/index.py` para Streamlit
```python
import os
import subprocess
import sys

def handler(request):
    # Set environment variables
    os.environ['STREAMLIT_SERVER_PORT'] = '8080'
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
    os.environ['API_BASE_URL'] = 'https://facturacion-api.vercel.app/api/v1'
    
    # Run Streamlit
    result = subprocess.run([
        sys.executable, '-m', 'streamlit', 'run', 'app.py',
        '--server.port', '8080',
        '--server.address', '0.0.0.0',
        '--server.headless', 'true'
    ], capture_output=True, text=True)
    
    return {
        'statusCode': 200,
        'body': result.stdout
    }
```

### 3.3 Actualizar `frontend/api_client.py`
```python
# Cambiar la línea 5
API_BASE = os.environ.get('API_BASE_URL', 'http://127.0.0.1:8000/api/v1')
```

---

## 🔧 Paso 4: Despliegue en Vercel

### 4.1 Preparar repositorio
```bash
# Commit todos los cambios
git add .
git commit -m "feat: Preparar para deploy Vercel + Supabase"

# Push a GitHub
git remote add origin https://github.com/tu-usuario/facturacion.git
git push -u origin master
```

### 4.2 Deploy Backend API
```bash
# 1. Ir a https://vercel.com
# 2. Import GitHub Repository
# 3. Seleccionar carpeta raíz
# 4. Configurar Environment Variables:
#    - SUPABASE_URL: postgresql://...
#    - SUPABASE_ANON_KEY: ...
#    - SUPABASE_SERVICE_KEY: ...
#    - SECRET_KEY: django-secret-key
#    - DEBUG: False
#    - SENTRY_DSN: (opcional)
# 5. Deploy
```

### 4.3 Deploy Frontend
```bash
# 1. Crear nuevo proyecto Vercel
# 2. Importar mismo repo
# 3. Root Directory: frontend/
# 4. Environment Variables:
#    - API_BASE_URL: https://facturacion-api.vercel.app/api/v1
# 5. Deploy
```

---

## 🔧 Paso 5: Migraciones y Setup

### 5.1 Ejecutar Migraciones
```python
# Crear script `migrate.py`
import os
import django
from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_prod')
django.setup()

execute_from_command_line(['manage.py', 'migrate'])
execute_from_command_line(['manage.py', 'createsuperuser'])
```

### 5.2 Configurar Supabase Auth (opcional)
```sql
-- Habilitar Row Level Security
ALTER TABLE app_empresa ENABLE ROW LEVEL SECURITY;
ALTER TABLE app_cliente ENABLE ROW LEVEL SECURITY;
-- ... etc para todas las tablas

-- Crear políticas
CREATE POLICY "Users can view their own company data" ON app_empresa
    FOR ALL USING (auth.uid() = ANY (
        SELECT user_id FROM app_membership WHERE empresa_id = app_empresa.id
    ));
```

---

## 🔧 Paso 6: Testing y Verificación

### 6.1 Checklist de Deploy
```bash
# Backend API Tests
curl https://facturacion-api.vercel.app/api/v1/auth/registro/
curl https://facturacion-api.vercel.app/api/v1/empresas/

# Frontend Tests
# Visitar https://facturacion-app.vercel.app
# Verificar login, creación empresa, CRUD operations

# Database Tests
# Conectar a Supabase y verificar tablas creadas
# Verificar datos aislados por empresa
```

### 6.2 Monitoring
```bash
# Vercel Analytics
# Supabase Logs
# Sentry Errors (si configurado)
```

---

## 📋 Environment Variables Summary

### Backend (Vercel Functions)
```
SUPABASE_URL=postgresql://postgres:[password]@db.[project].supabase.co:5432/postgres
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SECRET_KEY=django-insecure-very-long-random-string
DEBUG=False
ALLOWED_HOSTS=*.vercel.app
SENTRY_DSN=https://[sentry-dsn]@sentry.io/[project-id]
```

### Frontend (Vercel)
```
API_BASE_URL=https://facturacion-api.vercel.app/api/v1
STREAMLIT_SERVER_PORT=8080
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

---

## 🚀 URLs Finales

- **Frontend**: https://facturacion-app.vercel.app
- **Backend API**: https://facturacion-api.vercel.app/api/v1
- **API Docs**: https://facturacion-api.vercel.app/api/docs/
- **Database**: Supabase Dashboard

---

## 📝 Notas Importantes

1. **Costos**: Vercel (Hobby tier) + Supabase (Free tier) = $0/mes inicialmente
2. **Performance**: Vercel Functions tiene cold starts, considerar cache
3. **Scaling**: Ambas plataformas escalan automáticamente
4. **Security**: Configurar CORS y autenticación correctamente
5. **Backups**: Supabase incluye backups automáticos

---

*Guía creada para deploy en Vercel + Supabase*  
*Fecha: 2 de abril de 2026*
