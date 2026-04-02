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


def main():
    print("Generando archivos Excel de ejemplo...")

    # Individual files
    clientes_df = generate_clientes(1000)
    productos_df = generate_productos(500)
    stock_df = generate_stock(500, 3)
    ventas_df = generate_ventas(5000, 1000, 500)

    # Save individual files
    clientes_df.to_excel(os.path.join(OUTPUT_DIR, 'clientes.xlsx'), index=False)
    print(f"  clientes.xlsx: {len(clientes_df)} filas")

    productos_df.to_excel(os.path.join(OUTPUT_DIR, 'productos.xlsx'), index=False)
    print(f"  productos.xlsx: {len(productos_df)} filas")

    stock_df.to_excel(os.path.join(OUTPUT_DIR, 'stock.xlsx'), index=False)
    print(f"  stock.xlsx: {len(stock_df)} filas")

    ventas_df.to_excel(os.path.join(OUTPUT_DIR, 'ventas.xlsx'), index=False)
    print(f"  ventas.xlsx: {len(ventas_df)} filas")

    # Save combined workbook
    combined_path = os.path.join(OUTPUT_DIR, 'importacion_completa.xlsx')
    with pd.ExcelWriter(combined_path, engine='openpyxl') as writer:
        clientes_df.to_excel(writer, sheet_name='clientes', index=False)
        productos_df.to_excel(writer, sheet_name='productos', index=False)
        stock_df.to_excel(writer, sheet_name='stock', index=False)
        ventas_df.to_excel(writer, sheet_name='ventas', index=False)
    print(f"  importacion_completa.xlsx: archivo combinado con 4 hojas")

    print(f"\nArchivos generados en: {OUTPUT_DIR}")
    print("Listo!")


if __name__ == '__main__':
    main()
