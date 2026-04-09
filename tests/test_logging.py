#!/usr/bin/env python
"""Test that logging is working correctly."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import logging

# Get loggers
logger_apps = logging.getLogger('apps')
logger_importacion = logging.getLogger('apps.importacion')
logger_tasks = logging.getLogger('apps.importacion.tasks')

print("\n[TEST LOGGING]")
print(f"1. Logger apps: {logger_apps}")
print(f"2. Logger importacion: {logger_importacion}")
print(f"3. Logger tasks: {logger_tasks}")

# Test logging at different levels
print("\n[ENVIANDO LOGS DE PRUEBA]")
logger_apps.debug("DEBUG desde apps")
logger_apps.info("INFO desde apps")
logger_importacion.debug("DEBUG desde apps.importacion")
logger_importacion.info("INFO desde apps.importacion")
logger_tasks.debug("DEBUG desde tasks")
logger_tasks.info("INFO desde tasks")

print("\n[VERIFICACIÓN]")
print(f"1. Verifica console arriba ↑")
print(f"2. Verifica archivo: logs/app.log")
print(f"3. Si ves los logs, el sistema está funcionando ✅")
print(f"4. Si NO ves logs en app.log, hay un problema de escritura ❌")

# Try to write directly to check permissions
log_file = "logs/app.log"
try:
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write("\n[TEST] Línea de prueba directa\n")
    print(f"\n✅ Archivo {log_file} es ESCRIBIBLE")
except Exception as e:
    print(f"\n❌ ERROR escribiendo {log_file}: {e}")

print("\n[FIN TEST]")
