"""Script para verificar el estado del módulo de contabilidad."""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, str(os.path.dirname(__file__)))

django.setup()

from apps.contabilidad.models import PlanCuentas, Asiento, CotizacionDiaria
from apps.empresas.models import Empresa

empresa = Empresa.objects.first()

print("\n" + "=" * 70)
print("ESTADO DEL MODULO DE CONTABILIDAD")
print("=" * 70)

cuentas = PlanCuentas.objects.filter(empresa=empresa).count()
print(f"\n[OK] Plan de Cuentas: {cuentas} cuentas")

asientos = Asiento.objects.filter(empresa=empresa).count()
print(f"[OK] Asientos: {asientos} asientos")

cotizaciones = CotizacionDiaria.objects.filter(empresa=empresa).count()
print(f"[OK] Cotizaciones: {cotizaciones} cotizaciones")

from apps.compras.models import Proveedor
proveedores = Proveedor.objects.filter(empresa=empresa, cuenta_contable__isnull=False).count()
total_proveedores = Proveedor.objects.filter(empresa=empresa).count()
print(f"[OK] Proveedores con cuenta: {proveedores}/{total_proveedores}")

print("\n" + "=" * 70)
print("INSTALACION COMPLETADA EXITOSAMENTE")
print("=" * 70)

# Mostrar primeras cuentas
print("\nPrimeras 5 cuentas creadas:")
for cuenta in PlanCuentas.objects.filter(empresa=empresa)[:5]:
    print(f"  - {cuenta.codigo_cuenta}: {cuenta.descripcion}")

print("\nMigraciones aplicadas:")
from django.db.migrations.loader import MigrationLoader
loader = MigrationLoader(None, ignore_no_migrations=True)
for app_label, count in sorted([(k.split('.')[0], len(list(g))) for k, g in __import__('itertools').groupby(sorted([k for k in loader.disk_migrations.keys()]), key=lambda x: x[0])]):
    print(f"  - {app_label}: {count} migracion(es)")

print("\n")
