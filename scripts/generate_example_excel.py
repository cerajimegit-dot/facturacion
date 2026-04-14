#!/usr/bin/env python
"""
Generate example Excel files for testing the import system.
Creates files with sample data for clientes, productos, stock, and ventas.

Usage:
    python scripts/generate_example_excel.py
"""
import os
import sys
import random
from datetime import date, timedelta

# Ensure pandas and openpyxl are available
try:
    import pandas as pd
    from openpyxl import Workbook
except ImportError:
    print("Install pandas and openpyxl first: pip install pandas openpyxl")
    sys.exit(1)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'examples')
os.makedirs(OUTPUT_DIR, exist_ok=True)


def generate_clientes(n=1000):
    """Generate n sample client rows."""
    sectores = ['Comercio', 'Industria', 'Servicios', 'Tecnología', 'Salud', 'Educación']
    zonas = ['Central', 'Norte', 'Sur', 'Este', 'Oeste', 'Capital']
    rows = []
    for i in range(1, n + 1):
        rows.append({
            'empresa_codigo': 'EMP001',
            'nombre': f'Cliente {i:04d} S.A.',
            'ruc': f'{80000000 + i}-{i % 10}',
            'telefono': f'0981{random.randint(100000, 999999)}',
            'email': f'cliente{i:04d}@ejemplo.com',
            'direccion_facturacion': f'Calle {i}, Asunción',
            'direccion_entrega': f'Av. Principal {i * 10}, Asunción',
            'tipo_cliente': random.choice(['persona', 'empresa']),
            'sector': random.choice(sectores),
            'zona': random.choice(zonas),
            'observaciones': f'Cliente de prueba #{i}' if i % 5 == 0 else '',
        })
    return pd.DataFrame(rows)


def generate_productos(n=500):
    """Generate n sample product rows."""
    categorias = ['Electrónica', 'Oficina', 'Limpieza', 'Herramientas', 'Software', 'Accesorios']
    rows = []
    for i in range(1, n + 1):
        precio = random.randint(10000, 5000000)
        rows.append({
            'empresa_codigo': 'EMP001',
            'sku': f'PROD-{i:05d}',
            'nombre': f'Producto {i:04d}',
            'descripcion': f'Descripción del producto {i}',
            'categoria': random.choice(categorias),
            'variante': random.choice(['', 'S', 'M', 'L', 'XL']) if i % 3 == 0 else '',
            'precio_unitario': precio,
            'costo': int(precio * 0.6),
            'imagen_url': f'https://ejemplo.com/img/prod{i}.jpg' if i % 10 == 0 else '',
        })
    return pd.DataFrame(rows)


def generate_stock(n_products=500, n_almacenes=3):
    """Generate stock entries for products across warehouses."""
    rows = []
    ubicaciones = ['A', 'B', 'C', 'D']
    for i in range(1, n_products + 1):
        for j in range(1, n_almacenes + 1):
            if random.random() > 0.4:  # Not all products in all warehouses
                rows.append({
                    'empresa_codigo': 'EMP001',
                    'sku': f'PROD-{i:05d}',
                    'almacen_codigo': f'ALM{j:02d}',
                    'cantidad': random.randint(0, 500),
                    'ubicacion': f'{random.choice(ubicaciones)}-{random.randint(1, 20):02d}',
                })
    return pd.DataFrame(rows)


def generate_ventas(n=5000, n_clientes=1000, n_productos=500):
    """Generate n sale line items grouped into ~n/3 sales."""
    rows = []
    num_ventas = n // 3
    metodos = ['efectivo', 'transferencia', 'tarjeta', 'cheque']
    estados = ['confirmada', 'facturada', 'pagada']
    base_date = date.today() - timedelta(days=365)

    for v in range(1, num_ventas + 1):
        cliente_idx = random.randint(1, n_clientes)
        fecha = base_date + timedelta(days=random.randint(0, 365))
        n_lineas = random.randint(1, 5)
        estado = random.choice(estados)
        metodo = random.choice(metodos)

        for _ in range(n_lineas):
            prod_idx = random.randint(1, n_productos)
            precio = random.randint(10000, 500000)
            rows.append({
                'empresa_codigo': 'EMP001',
                'numero': f'FAC-{v:06d}',
                'fecha': fecha.strftime('%Y-%m-%d'),
                'cliente_ruc': f'{80000000 + cliente_idx}-{cliente_idx % 10}',
                'sku': f'PROD-{prod_idx:05d}',
                'cantidad': random.randint(1, 20),
                'precio_unitario': precio,
                'impuestos': 10,
                'estado': estado,
                'metodo_pago': metodo,
            })

    return pd.DataFrame(rows[:n])  # Cap at n rows


def generate_compras(n=3000, n_proveedores=200, n_productos=500):
    """Generate n purchase line items grouped into ~n/3 purchases."""
    rows = []
    num_compras = n // 3
    base_date = date.today() - timedelta(days=365)

    for c in range(1, num_compras + 1):
        prov_idx = random.randint(1, n_proveedores)
        fecha = base_date + timedelta(days=random.randint(0, 365))
        n_lineas = random.randint(1, 5)
        condiciones = ['gravada_10', 'gravada_5', 'exenta']

        for _ in range(n_lineas):
            prod_idx = random.randint(1, n_productos)
            precio = random.randint(5000, 3000000)
            rows.append({
                'numero': f'COMP-{c:06d}',
                'fecha': fecha.strftime('%Y-%m-%d'),
                'proveedor_ruc': f'{90000000 + prov_idx}-{prov_idx % 10}',
                'proveedor_nombre': f'Proveedor {prov_idx:04d} S.R.L.',
                'proveedor_pais': 'Paraguay',
                'descripcion': f'Item compra #{c}-{_+1}',
                'cantidad': random.randint(1, 50),
                'precio_unitario': precio,
                'condicion_iva': random.choice(condiciones),
                'sku': f'PROD-{prod_idx:05d}',
                'almacen_codigo': f'ALM{random.randint(1, 3):02d}',
                'moneda': 'PYG',
                'notas': f'OC #{c}' if c % 5 == 0 else '',
            })

    return pd.DataFrame(rows[:n])


def generate_activos_fijos(n=200):
    """Generate n asset rows."""
    tipos = ['IT', 'planta', 'mobiliario', 'vehiculo', 'edificio', 'terreno', 'otro']
    clasificaciones = ['Equipos de Oficina', 'Maquinaria Industrial', 'Vehículos',
                       'Mobiliario', 'Equipos IT', 'Herramientas', 'Edificios']
    plantas = ['Central', 'Sucursal Norte', 'Sucursal Sur', 'Deposito']
    edificios = ['Edificio A', 'Edificio B', 'Galpon 1', 'Galpon 2', '']
    areas = ['Oficina', 'Produccion', 'Almacen', 'Taller', '']
    rows = []

    for i in range(1, n + 1):
        tipo = random.choice(tipos)
        valor = random.randint(500000, 50000000)
        vida = random.randint(3, 20)
        fecha = date.today() - timedelta(days=random.randint(30, 1800))
        rows.append({
            'codigo': f'AF-{i:05d}',
            'nombre': f'Activo Fijo {i:04d}',
            'tipo': tipo,
            'descripcion': f'Descripción del activo {i}',
            'valor_adquisicion': valor,
            'valor_residual': int(valor * 0.1),
            'vida_util_anios': vida,
            'fecha_adquisicion': fecha.strftime('%Y-%m-%d'),
            'moneda': 'PYG',
            'clasificacion': random.choice(clasificaciones),
            'ubicacion_planta': random.choice(plantas),
            'ubicacion_edificio': random.choice(edificios),
            'ubicacion_area': random.choice(areas),
            'centro_costo_codigo': f'CC{random.randint(1, 10):03d}',
            'centro_costo_descripcion': f'Centro de Costo {random.randint(1, 10)}',
            'numero_serie': f'SN-{random.randint(100000, 999999)}' if i % 3 == 0 else '',
            'numero_factura': f'FAC-{random.randint(1, 500):06d}' if i % 2 == 0 else '',
            'propiedad_terceros': 'SI' if i % 20 == 0 else 'NO',
        })

    return pd.DataFrame(rows)


def main():
    print("Generando archivos Excel de ejemplo...")

    # Individual files
    clientes_df = generate_clientes(1000)
    productos_df = generate_productos(500)
    stock_df = generate_stock(500, 3)
    ventas_df = generate_ventas(5000, 1000, 500)
    compras_df = generate_compras(3000, 200, 500)
    activos_df = generate_activos_fijos(200)

    # Save individual files
    clientes_df.to_excel(os.path.join(OUTPUT_DIR, 'clientes.xlsx'), index=False)
    print(f"  clientes.xlsx: {len(clientes_df)} filas")

    productos_df.to_excel(os.path.join(OUTPUT_DIR, 'productos.xlsx'), index=False)
    print(f"  productos.xlsx: {len(productos_df)} filas")

    stock_df.to_excel(os.path.join(OUTPUT_DIR, 'stock.xlsx'), index=False)
    print(f"  stock.xlsx: {len(stock_df)} filas")

    ventas_df.to_excel(os.path.join(OUTPUT_DIR, 'ventas.xlsx'), index=False)
    print(f"  ventas.xlsx: {len(ventas_df)} filas")

    compras_df.to_excel(os.path.join(OUTPUT_DIR, 'compras.xlsx'), index=False)
    print(f"  compras.xlsx: {len(compras_df)} filas")

    activos_df.to_excel(os.path.join(OUTPUT_DIR, 'activos_fijos.xlsx'), index=False)
    print(f"  activos_fijos.xlsx: {len(activos_df)} filas")

    # Save combined workbook
    combined_path = os.path.join(OUTPUT_DIR, 'importacion_completa.xlsx')
    with pd.ExcelWriter(combined_path, engine='openpyxl') as writer:
        clientes_df.to_excel(writer, sheet_name='clientes', index=False)
        productos_df.to_excel(writer, sheet_name='productos', index=False)
        stock_df.to_excel(writer, sheet_name='stock', index=False)
        ventas_df.to_excel(writer, sheet_name='ventas', index=False)
        compras_df.to_excel(writer, sheet_name='compras', index=False)
        activos_df.to_excel(writer, sheet_name='activos_fijos', index=False)
    print(f"  importacion_completa.xlsx: archivo combinado con 6 hojas")

    print(f"\nArchivos generados en: {OUTPUT_DIR}")
    print("Listo!")


if __name__ == '__main__':
    main()
