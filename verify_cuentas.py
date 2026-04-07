"""Script para verificar cuentas cargadas."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, str(os.path.dirname(__file__)))

django.setup()

from apps.contabilidad.models import PlanCuentas
from apps.empresas.models import Empresa

empresa = Empresa.objects.get(nombre="Eleva Supply")

cuentas = PlanCuentas.objects.filter(empresa=empresa).all()

print("\n" + "=" * 70)
print("CUENTAS CONTABLES CARGADAS")
print("=" * 70)

print(f"\nTotal: {cuentas.count()} cuentas")

print("\nPrimeras 10 cuentas:")
for i, cuenta in enumerate(cuentas[:10], 1):
    print(f"  {i}. {cuenta.codigo_cuenta} - {cuenta.descripcion[:60]}")

print("\nÚltimas 5 cuentas:")
for i, cuenta in enumerate(cuentas.reverse()[:5], 1):
    print(f"  {i}. {cuenta.codigo_cuenta} - {cuenta.descripcion[:60]}")

# Mostrar resumen por condición
from django.db.models import Count
por_condicion = cuentas.values('condicion').annotate(cantidad=Count('id'))
print("\nCuentas por condición:")
for item in por_condicion:
    print(f"  - {item['condicion']}: {item['cantidad']}")

print("\n" + "=" * 70 + "\n")
