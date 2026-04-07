#!/usr/bin/env python
"""
Test: Frontend Flow - Simula lo que Streamlit hace
1. Buscar productos
2. Crear nuevo producto si no existe  
3. Crear compra con detalles desde Streamlit
"""
import os
import sys
import django
from decimal import Decimal
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_test_local')
django.setup()

from apps.productos.models import Producto
from apps.empresas.models import Empresa
from apps.compras.models import Proveedor, Compra, CompraDetalle
from apps.inventario.models import Almacen
from apps.usuarios.models import Usuario

def setup():
    """Setup datos iniciales"""
    empresa, _ = Empresa.objects.get_or_create(
        nombre="Empresa Test",
        defaults={"activo": True}
    )
    usuario, created = Usuario.objects.get_or_create(
        username="test_admin",
        defaults={
            "email": "admin@test.com",
            "is_staff": True,
            "is_superuser": True,
            "empresa": empresa
        }
    )
    if created:
        usuario.set_password("admin123")
        usuario.save()
    
    proveedor, _ = Proveedor.objects.get_or_create(
        empresa=empresa,
        ruc_numero="80081234",
        defaults={
            "nombre": "Proveedor Principal",
            "pais": "Paraguay"
        }
    )
    
    almacen, _ = Almacen.objects.get_or_create(
        empresa=empresa,
        codigo="ALM001",
        defaults={
            "nombre": "Almacén Principal",
            "direccion": "Asunción"
        }
    )
    
    return empresa, usuario, proveedor, almacen

def test_frontend_flow():
    """Simular flujo completo del frontend"""
    print("\n" + "="*80)
    print("TEST: FLUJO COMPLETO FRONTEND")
    print("="*80)
    
    empresa, usuario, proveedor, almacen = setup()
    
    print("\n🔍 PASO 1: Usuario busca productos")
    print("-" * 80)
    
    search_term = "laptop"
    productos_encontrados = Producto.objects.filter(
        empresa=empresa,
        nombre__icontains=search_term
    )
    print(f"  Búsqueda: '{search_term}'")
    print(f"  Productos encontrados: {productos_encontrados.count()}")
    
    if not productos_encontrados.exists():
        print(f"\n📝 PASO 2: Crear nuevo producto (no existe '{search_term}')")
        print("-" * 80)
        
        # Este es el flujo cuando usuario hace click en "Crear nuevo"
        nuevo_producto = Producto.objects.create(
            empresa=empresa,
            sku="LAP-001",
            nombre="Laptop HP 15 - Test",
            tipo="producto",
            precio_unitario=Decimal("2500000.00"),
            impuesto_porcentaje=Decimal("10.00"),
            descripcion="Laptop de prueba desde frontend"
        )
        print(f"  ✓ Producto creado: {nuevo_producto.nombre}")
        print(f"    SKU: {nuevo_producto.sku}")
        print(f"    Precio: ₲{nuevo_producto.precio_unitario}")
        
        # Actualizar búsqueda con el nuevo producto
        productos_encontrados = Producto.objects.filter(
            empresa=empresa,
            nombre__icontains=search_term
        )
    
    print(f"\n  ✓ Productos disponibles ahora:")
    for idx, prod in enumerate(productos_encontrados, 1):
        print(f"    {idx}. [{prod.sku}] {prod.nombre} - ₲{prod.precio_unitario}")
    
    # Seleccionar el primero para agregar a la compra
    producto_seleccionado = productos_encontrados.first()
    
    print(f"\n✅ PASO 3: Agregar item a compra")
    print("-" * 80)
    print(f"  Producto seleccionado: {producto_seleccionado.nombre}")
    print(f"  SKU: {producto_seleccionado.sku}")
    print(f"  Precio: ₲{producto_seleccionado.precio_unitario}")
    
    # Simular: usuario ingresa cantidad y le da agregar
    items = [
        {
            'producto': producto_seleccionado,
            'cantidad': Decimal("1"),
            'precio_unitario': producto_seleccionado.precio_unitario,
            'impuesto_porcentaje': Decimal("10.00"),
            'descripcion': producto_seleccionado.nombre
        }
    ]
    
    # Buscar otro producto existente y agregarlo
    print(f"\n📦 PASO 4: Agregar más items desde búsqueda")
    print("-" * 80)
    
    otro_producto = Producto.objects.filter(
        empresa=empresa,
        nombre__icontains="test"
    ).exclude(sku="LAP-001").first()
    
    if otro_producto:
        print(f"  ✓ Encontrado: {otro_producto.nombre}")
        items.append({
            'producto': otro_producto,
            'cantidad': Decimal("2"),
            'precio_unitario': otro_producto.precio_unitario,
            'impuesto_porcentaje': Decimal("10.00"),
            'descripcion': otro_producto.nombre
        })
    else:
        # Crear otro producto de prueba
        otro_prod = Producto.objects.create(
            empresa=empresa,
            sku="MOUSE-001",
            nombre="Mouse Inalámbrico",
            tipo="producto",
            precio_unitario=Decimal("150000.00"),
            impuesto_porcentaje=Decimal("10.00")
        )
        print(f"  ✓ Creado: {otro_prod.nombre}")
        items.append({
            'producto': otro_prod,
            'cantidad': Decimal("2"),
            'precio_unitario': otro_prod.precio_unitario,
            'impuesto_porcentaje': Decimal("10.00"),
            'descripcion': otro_prod.nombre
        })
    
    print(f"\n💾 PASO 5: Usuario registra la compra")
    print("-" * 80)
    
    # Crear compra (como lo hace el serializer)
    compra = Compra.objects.create(
        empresa=empresa,
        numero=f"FRONTEND-{int(__import__('time').time()*1000)}",
        fecha=date.today(),
        proveedor=proveedor,
        almacen=almacen,
        usuario_registra=usuario,
        moneda='PYG',
        notas="Compra de prueba desde frontend"
    )
    print(f"  ✓ Compra creada: {compra.numero}")
    
    # Crear detalles y calcular totales
    subtotal = Decimal("0")
    impuestos = Decimal("0")
    
    for idx, item in enumerate(items, 1):
        detalle = CompraDetalle.objects.create(
            compra=compra,
            empresa=empresa,
            descripcion=item['descripcion'],
            cantidad=item['cantidad'],
            precio_unitario=item['precio_unitario'],
            impuesto_porcentaje=item['impuesto_porcentaje'],
            es_servicio=False,
            producto=item['producto']
        )
        
        item_subtotal = item['cantidad'] * item['precio_unitario']
        item_impuestos = item_subtotal * (item['impuesto_porcentaje'] / Decimal("100"))
        
        subtotal += item_subtotal
        impuestos += item_impuestos
        
        print(f"\n  Item {idx}:")
        print(f"    {detalle.descripcion}")
        print(f"    Cantidad: {detalle.cantidad}")
        print(f"    Precio unitario: ₲{detalle.precio_unitario}")
        print(f"    Subtotal: ₲{item_subtotal}")
        print(f"    Impuesto ({item['impuesto_porcentaje']}%): ₲{item_impuestos}")
        print(f"    Total: ₲{item_subtotal + item_impuestos}")
    
    # Actualizar totales en compra
    total = subtotal + impuestos
    compra.subtotal = subtotal
    compra.impuestos_total = impuestos
    compra.total = total
    compra.save()
    
    # Verificar
    compra.refresh_from_db()
    
    print(f"\n" + "="*80)
    print("✅ COMPRA REGISTRADA EXITOSAMENTE")
    print("="*80)
    print(f"  Número: {compra.numero}")
    print(f"  Proveedor: {compra.proveedor.nombre}")
    print(f"  Items: {compra.detalles.count()}")
    print(f"\n  💰 TOTALES:")
    print(f"    Subtotal: ₲{compra.subtotal:,.2f}")
    print(f"    Impuestos: ₲{compra.impuestos_total:,.2f}")
    print(f"    Total: ₲{compra.total:,.2f}")
    print(f"\n  Estado: {compra.estado}")
    print(f"  Creada por: {compra.usuario_registra.username if compra.usuario_registra else 'Sistema'}")
    print(f"  Fecha: {compra.fecha}")
    
    return True

def main():
    print("\n" + "="*80)
    print("PRUEBAS: Flujo Frontend Streamlit")
    print("="*80)
    
    try:
        resultado = test_frontend_flow()
        if resultado:
            print(f"\n🎉 FLUJO FRONTEND COMPLETADO EXITOSAMENTE")
        return 0
    except Exception as e:
        print(f"\n❌ Error en flujo: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
