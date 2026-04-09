#!/usr/bin/env python
"""
Test: Backend API - Crear Compra directamente
Simula lo que el frontend hace al enviar un formulario
"""
import os
import sys
import django
from decimal import Decimal
from datetime import date

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings_test_local')
django.setup()

# Importar necesario
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from apps.empresas.models import Empresa
from apps.compras.models import Proveedor, Compra, CompraDetalle
from apps.inventario.models import Almacen
from apps.usuarios.models import Usuario

# Setup
client = APIClient()
BASE_URL = "http://localhost:8000/api"

def setup_test_data():
    """Crear datos de prueba"""
    print("🔧 Preparando datos de prueba...")
    
    # Empresa
    empresa, _ = Empresa.objects.get_or_create(
        nombre="Empresa Test",
        defaults={"activo": True}
    )
    print(f"  ✓ Empresa: {empresa.nombre}")
    
    # Usuario con staff
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
    print(f"  ✓ Usuario: {usuario.username}")
    
    # Proveedor
    proveedor, _ = Proveedor.objects.get_or_create(
        empresa=empresa,
        ruc_numero="80081234",
        defaults={
            "nombre": "Proveedor Principal",
            "pais": "Paraguay"
        }
    )
    print(f"  ✓ Proveedor: {proveedor.nombre}")
    
    # Almacén
    almacen, _ = Almacen.objects.get_or_create(
        empresa=empresa,
        codigo="ALM001",
        defaults={
            "nombre": "Almacén Principal",
            "direcion": "Asunción"
        }
    )
    print(f"  ✓ Almacén: {almacen.nombre}")
    
    return usuario, empresa, proveedor, almacen

def test_create_compra_direct():
    """Test 1: Crear compra directamente (bypass de serializer)"""
    print("\n" + "="*60)
    print("TEST 1: Crear Compra Directamente (ORM)")
    print("="*60)
    
    usuario, empresa, proveedor, almacen = setup_test_data()
    
    try:
        # Crear compra como lo haría el sistema internamente
        compra = Compra.objects.create(
            empresa=empresa,
            numero=f"DIRECT-{int(__import__('time').time()*1000)}",
            fecha=date.today(),
            proveedor=proveedor,
            almacen=almacen,
            usuario_registra=usuario,
            moneda='PYG',
            notas="Compra de prueba backend directo"
        )
        print(f"✓ Compra creada: {compra.numero} ({compra.id})")
        
        # Crear detalles
        detalle1 = CompraDetalle.objects.create(
            compra=compra,
            empresa=empresa,
            descripcion="Servicio de consultoría",
            cantidad=Decimal("1.00"),
            precio_unitario=Decimal("50000.00"),
            impuesto_porcentaje=Decimal("10.00"),
            es_servicio=True
        )
        print(f"✓ Detalle 1: {detalle1.descripcion} - ₲{detalle1.precio_unitario}")
        
        detalle2 = CompraDetalle.objects.create(
            compra=compra,
            empresa=empresa,
            descripcion="Soporte técnico mensual",
            cantidad=Decimal("1.00"),
            precio_unitario=Decimal("30000.00"),
            impuesto_porcentaje=Decimal("10.00"),
            es_servicio=True
        )
        print(f"✓ Detalle 2: {detalle2.descripcion} - ₲{detalle2.precio_unitario}")
        
        # Actualizar totales de la compra
        compra.subtotal = Decimal("80000.00")
        compra.impuestos_total = Decimal("8000.00")
        compra.total = Decimal("88000.00")
        compra.save()
        
        # Verificar
        compra.refresh_from_db()
        print(f"\n✅ RESULTADO:")
        print(f"  Subtotal: ₲{compra.subtotal}")
        print(f"  Impuestos: ₲{compra.impuestos_total}")
        print(f"  Total: ₲{compra.total}")
        print(f"  Estado: {compra.estado}")
        print(f"  Detalles: {compra.detalles.count()} items")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_create_compra_via_serializer():
    """Test 2: Crear compra vía serializer (como lo hace el frontend)"""
    print("\n" + "="*60)
    print("TEST 2: Crear Compra vía Serializer")
    print("="*60)
    
    usuario, empresa, proveedor, almacen = setup_test_data()
    
    try:
        from apps.compras.serializers import CompraSerializer
        
        # Payload como lo enviaría Streamlit
        payload = {
            'numero': f'SERIALIZER-{int(__import__("time").time()*1000)}',
            'fecha': str(date.today()),
            'proveedor': str(proveedor.id),
            'almacen': str(almacen.id),
            'moneda': 'PYG',
            'notas': 'Compra de prueba vía serializer',
            'detalles': [
                {
                    'descripcion': 'Materiales de oficina',
                    'cantidad': 10,
                    'precio_unitario': 15000,
                    'impuesto_porcentaje': 10
                },
                {
                    'descripcion': 'Equipos de cómputo',
                    'cantidad': 2,
                    'precio_unitario': 100000,
                    'impuesto_porcentaje': 10
                }
            ]
        }
        
        # Crear compra via serializer
        serializer = CompraSerializer(
            data=payload,
            context={'request': type('Request', (), {'user': usuario})()}
        )
        
        if serializer.is_valid():
            compra = serializer.save(usuario_registra=usuario)
            print(f"✓ Compra creada: {compra.numero}")
            
            # Verificar totales calculados automáticamente
            compra.refresh_from_db()
            print(f"\n✅ RESULTADO:")
            print(f"  Subtotal: ₲{compra.subtotal}")
            print(f"  Impuestos: ₲{compra.impuestos_total}")
            print(f"  Total: ₲{compra.total}")
            print(f"  Detalles creados: {compra.detalles.count()}")
            
            # Detalle línea por línea
            for idx, detalle in enumerate(compra.detalles.all(), 1):
                print(f"\n  Item {idx}: {detalle.descripcion}")
                print(f"    Qty: {detalle.cantidad} x ₲{detalle.precio_unitario}")
                print(f"    Subtotal: ₲{detalle.subtotal}")
                print(f"    Impuesto: ₲{detalle.impuestos} ({detalle.impuesto_porcentaje}%)")
                print(f"    Total: ₲{detalle.total}")
            
            return True
        else:
            print(f"❌ Errores de validación:")
            for field, errors in serializer.errors.items():
                print(f"  {field}: {errors}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("\n" + "="*60)
    print("PRUEBAS: Backend API - Módulo Compras")
    print("="*60)
    
    results = []
    results.append(("Backend Directo (ORM)", test_create_compra_direct()))
    results.append(("Backend vía Serializer", test_create_compra_via_serializer()))
    
    print("\n" + "="*60)
    print("RESUMEN")
    print("="*60)
    for test_name, passed in results:
        status = "✅ PASÓ" if passed else "❌ FALLÓ"
        print(f"{status}: {test_name}")
    
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n🎉 TODOS LOS TESTS DEL BACKEND PASARON")
    else:
        print("\n⚠️ ALGUNOS TESTS FALLARON")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
