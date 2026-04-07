#!/usr/bin/env python
"""Verificar si la compra se registró y el stock se ingresó."""
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.compras.models import Compra, CompraDetalle
from apps.inventario.models import Movimiento

# Buscar compra con descripción "asc1"
detalles = CompraDetalle.objects.filter(descripcion__icontains="asc1")

if detalles.exists():
    print("=" * 70)
    print("✓ COMPRA ENCONTRADA")
    print("=" * 70)
    for detalle in detalles:
        compra = detalle.compra
        print(f"\n📋 INFORMACIÓN DE LA COMPRA:")
        print(f"  - ID: {compra.id}")
        print(f"  - Número: {compra.numero}")
        print(f"  - Estado: {compra.estado}")
        print(f"  - Proveedor: {compra.proveedor.nombre if compra.proveedor else 'N/A'}")
        print(f"  - Almacén destino: {compra.almacen.nombre if compra.almacen else 'N/A'}")
        print(f"  - Fecha: {compra.fecha}")
        
        print(f"\n📦 DETALLE DEL ITEM:")
        print(f"  - Descripción: {detalle.descripcion}")
        print(f"  - Cantidad: {detalle.cantidad}")
        print(f"  - Precio unitario: {detalle.precio_unitario}")
        print(f"  - IVA%: {detalle.impuesto_porcentaje}")
        total = detalle.cantidad * detalle.precio_unitario * (1 + detalle.impuesto_porcentaje / 100)
        print(f"  - Total: {total}")
        
        # Buscar movimientos de stock
        movimientos = Movimiento.objects.filter(compra_id=compra.id, detalle_compra_id=detalle.id)
        
        print(f"\n📊 MOVIMIENTOS DE STOCK:")
        if movimientos.exists():
            for mov in movimientos:
                print(f"  ✓ Movimiento registrado:")
                print(f"    - ID: {mov.id}")
                print(f"    - Tipo: {mov.tipo_movimiento}")
                print(f"    - Almacén: {mov.almacen.nombre}")
                print(f"    - Cantidad: {mov.cantidad}")
                print(f"    - Fecha: {mov.fecha}")
                print(f"    - Usuario: {mov.usuario.email if mov.usuario else 'Sistema'}")
        else:
            print(f"  ✗ NO hay movimientos de stock registrados para este item")
            
        # Verificar stock actual
        from apps.inventario.models import Stock
        stocks = Stock.objects.filter(almacen_id=compra.almacen.id, producto__isnull=False)
        print(f"\n💾 STOCK ACTUAL EN ALMACÉN '{compra.almacen.nombre if compra.almacen else 'N/A'}':")
        if stocks.exists():
            for stock in stocks:
                print(f"  - {stock.producto.nombre}: {stock.cantidad} unidades")
        else:
            print(f"  - No hay stock registrado en este almacén")
else:
    print("✗ No se encontró compra con descripción 'asc1'")
    print("\nÚltimas compras registradas:")
    compras = Compra.objects.all().order_by('-fecha')[:5]
    for compra in compras:
        print(f"  - {compra.numero} ({compra.estado})")
