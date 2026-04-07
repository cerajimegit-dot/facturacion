#!/usr/bin/env python
"""Script para generar y ejecutar migraciones del módulo de contabilidad."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, str(os.path.dirname(__file__)))

django.setup()

from django.core.management import call_command

print("=" * 70)
print("[GENERANDO Y APLICANDO MIGRACIONES]")
print("=" * 70)

try:
    print("\n[1] Generando migraciones para apps.contabilidad...")
    call_command('makemigrations', 'contabilidad', verbosity=2)
    print("[OK] Migraciones de contabilidad generadas")
except Exception as e:
    print(f"[ERROR] {str(e)}")
    sys.exit(1)

try:
    print("\n[2] Generando migraciones para apps.compras...")
    call_command('makemigrations', 'compras', verbosity=2)
    print("[OK] Migraciones de compras generadas")
except Exception as e:
    print(f"[WARNING] {str(e)}")

try:
    print("\n[3] Generando migraciones para apps.productos...")
    call_command('makemigrations', 'productos', verbosity=2)
    print("[OK] Migraciones de productos generadas")
except Exception as e:
    print(f"[WARNING] {str(e)}")

try:
    print("\n[4] Aplicando todas las migraciones...")
    call_command('migrate', verbosity=2)
    print("[OK] Todas las migraciones aplicadas")
except Exception as e:
    print(f"[ERROR] Error aplicando migraciones: {str(e)}")
    sys.exit(1)

print("\n" + "=" * 70)
print("[OK] MIGRACIONES COMPLETADAS EXITOSAMENTE")
print("=" * 70)
