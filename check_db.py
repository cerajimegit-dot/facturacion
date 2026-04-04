#!/usr/bin/env python
"""Check database for clientes and productos."""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.clientes.models import Cliente
from apps.empresas.models import Empresa
from apps.productos.models import Producto

print('=== CLIENTES ===')
clientes = Cliente.objects.all()
print(f'Total clientes: {clientes.count()}')
for c in clientes[:5]:
    emp = c.empresa.nombre if c.empresa else "sin empresa"
    print(f'  - {c.nombre} ({emp})')

print('\n=== EMPRESAS ===')
empresas = Empresa.objects.all()
print(f'Total empresas: {empresas.count()}')
for e in empresas[:5]:
    print(f'  - {e.nombre}')

print('\n=== PRODUCTOS ===')
productos = Producto.objects.all()
print(f'Total productos: {productos.count()}')
for p in productos[:5]:
    emp = p.empresa.nombre if hasattr(p, 'empresa') and p.empresa else "sin empresa"
    print(f'  - {p.nombre} ({emp})')
