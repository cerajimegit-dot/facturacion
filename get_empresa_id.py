"""Script para obtener UUID de la empresa."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, str(os.path.dirname(__file__)))

django.setup()

from apps.empresas.models import Empresa

for empresa in Empresa.objects.all():
    print(f"ID: {empresa.id}")
    print(f"Nombre: {empresa.nombre}")
    print()
