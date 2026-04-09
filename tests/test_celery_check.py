#!/usr/bin/env python
"""Check if Celery is available and configured correctly."""
import os
import django
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

print("[Celery Check]")

# Check if Celery broker is accessible
from config.celery import app as celery_app

print(f"1. Celery app: {celery_app}")
print(f"2. Broker URL: {celery_app.conf.broker_url}")

# Try to ping broker
try:
    result = celery_app.control.inspect().ping()
    if result:
        print(f"✅ Broker está disponible: {result}")
    else:
        print("❌ Broker responde pero sin workers activos")
except Exception as e:
    print(f"❌ ERROR conectando a broker: {e}")

# Try to check if tasks are registered
try:
    result = celery_app.control.inspect().registered()
    if result:
        print(f"✅ Tasks registradas: {list(result.keys())}")
    else:
        print("❌ No hay workers disponibles para verificar tasks")
except Exception as e:
    print(f"❌ ERROR verificando tasks: {e}")

# Check import task specifically
try:
    from apps.importacion.tasks import validate_import_task, execute_import_task
    print(f"✅ validate_import_task cargada: {validate_import_task}")
    print(f"✅ execute_import_task cargada: {execute_import_task}")
except Exception as e:
    print(f"❌ ERROR cargando tasks: {e}")

print("\n[Recomendación]")
print("Si Broker no está disponible, inicia Celery:")
print("  celery -A config worker -l info")
print("En otra terminal, inicia el servidor Django:")
print("  python manage.py runserver")

