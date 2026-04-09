#!/usr/bin/env python
"""Probar creación de compra con detalles."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.compras.models import Compra, Proveedor, CategoriaGasto
from apps.inventario.models import Almacen
from apps.empresas.models import Empresa
from apps.compras.serializers import CompraSerializer
from rest_framework.test import APIRequestFactory
from rest_framework.request import Request

# Obtener datos de prueba
try:
    empresa = Empresa.objects.first()
    proveedor = Proveedor.objects.filter(empresa=empresa).first()
    almacen = Almacen.objects.filter(empresa=empresa).first()
    
    if not proveedor:
        print("❌ No hay proveedores. Debe crear uno primero.")
    elif not almacen:
        print("❌ No hay almacenes. Debe crear uno primero.")
    else:
        print("✓ Datos disponibles")
        print(f"  - Empresa: {empresa.nombre}")
        print(f"  - Proveedor: {proveedor.nombre}")
        print(f"  - Almacén: {almacen.nombre}")
        
        # Datos de test
        import datetime
        numero_unico = f"TEST-{datetime.datetime.now().timestamp()}"
        payload = {
            "numero": numero_unico,
            "fecha": "2026-04-04",
            "proveedor": str(proveedor.id),
            "almacen": str(almacen.id),
            "moneda": "PYG",
            "detalles": [
                {
                    "descripcion": "Test Item 1",
                    "cantidad": 10,
                    "precio_unitario": 1000,
                    "impuesto_porcentaje": 10
                },
                {
                    "descripcion": "Test Item 2",
                    "cantidad": 5,
                    "precio_unitario": 2000,
                    "impuesto_porcentaje": 10
                }
            ]
        }
        
        print("\n📝 Payload a enviar:")
        print(payload)
        
        # Crear serializer
        serializer = CompraSerializer(data=payload)
        
        if serializer.is_valid():
            print("\n✅ Validación OK")
            compra = serializer.save(empresa=empresa)
            print(f"\n✓ Compra creada:")
            print(f"  - ID: {compra.id}")
            print(f"  - Número: {compra.numero}")
            print(f"  - Subtotal: {compra.subtotal}")
            print(f"  - Impuestos: {compra.impuestos_total}")
            print(f"  - Total: {compra.total}")
            print(f"  - Detalles: {compra.compradetalle_set.count()}")
        else:
            print("\n❌ Errores de validación:")
            for field, errors in serializer.errors.items():
                print(f"  - {field}: {errors}")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
