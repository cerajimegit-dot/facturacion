#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.contabilidad.models import PlanCuentas
from apps.empresas.models import Empresa

# Obtener la primera empresa o crear una si no existe
try:
    empresa = Empresa.objects.first()
    if not empresa:
        print("❌ No hay empresas registradas. Crea una empresa primero.")
        exit(1)
except Exception as e:
    print(f"❌ Error obteniendo empresa: {e}")
    exit(1)

# Cuentas pasivas comunes (empiezan con 2)
cuentas_pasivas = [
    ('2110', 'Proveedores'),
    ('2111', 'Proveedores Nacionales'),
    ('2112', 'Proveedores Importación'),
    ('2120', 'Impuestos por Pagar'),
    ('2121', 'IVA por Pagar'),
    ('2122', 'Impuesto a la Renta por Pagar'),
    ('2130', 'Salarios y Beneficios por Pagar'),
    ('2131', 'Salarios por Pagar'),
    ('2132', 'Beneficios Sociales por Pagar'),
    ('2140', 'Cargas Fiscales por Pagar'),
    ('2141', 'IPS por Pagar'),
    ('2142', 'ISSEPS por Pagar'),
    ('2200', 'Préstamos a Largo Plazo'),
    ('2210', 'Préstamos Bancarios LP'),
    ('2220', 'Créditos Hipotecarios'),
    ('2300', 'Otras Cuentas por Pagar'),
    ('2310', 'Anticipos de Clientes'),
    ('2320', 'Créditos por Impuestos'),
]

created = 0
skipped = 0

for cod, desc in cuentas_pasivas:
    if not PlanCuentas.objects.filter(empresa=empresa, codigo_cuenta=cod).exists():
        PlanCuentas.objects.create(
            empresa=empresa,
            codigo_cuenta=cod,
            descripcion=desc,
            condicion='acreedora',
            clase='analitica',
            activa=True
        )
        created += 1
        print(f"✅ Creada: {cod} - {desc}")
    else:
        skipped += 1
        print(f"⏭️  Existente: {cod}")

total = PlanCuentas.objects.filter(empresa=empresa).count()
print(f"\n📊 Resumen para empresa '{empresa.nombre}':")
print(f"  - Creadas: {created}")
print(f"  - Omitidas: {skipped}")
print(f"  - Total cuentas: {total}")
print(f"\n✅ Cuentas pasivas agregadas correctamente!")
