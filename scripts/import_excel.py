#!/usr/bin/env python
"""
Standalone script for importing data from Excel files.

Usage:
    python scripts/import_excel.py --empresa CODIGO --file path/to/file.xlsx --tipo clientes
    python scripts/import_excel.py --empresa CODIGO --file path/to/file.xlsx --tipo mixto

The script can be run from the project root with Django settings configured.
"""
import os
import sys
import argparse
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

import pandas as pd
from decimal import Decimal
from django.db import transaction

from apps.empresas.models import Empresa
from apps.clientes.models import Cliente
from apps.productos.models import Producto, Categoria
from apps.inventario.models import Almacen, Stock
from apps.ventas.models import Venta, LineaVenta
from apps.importacion.validators import (
    validate_clientes_row, validate_productos_row,
    validate_stock_row, validate_ventas_row,
)


def print_report(sheet_name, results):
    """Print validation report for a sheet."""
    valid = sum(1 for r in results if r['valida'])
    errors = sum(1 for r in results if not r['valida'])
    warnings = sum(1 for r in results if r['warnings'])

    print(f"\n{'='*60}")
    print(f"  Hoja: {sheet_name}")
    print(f"  Total filas: {len(results)}")
    print(f"  Válidas: {valid}")
    print(f"  Con errores: {errors}")
    print(f"  Con warnings: {warnings}")
    print(f"{'='*60}")

    if errors > 0:
        print("\n  Errores:")
        for r in results:
            if not r['valida']:
                print(f"    Fila {r['fila']}: {', '.join(r['errores'])}")

    if warnings > 0:
        print("\n  Warnings:")
        for r in results:
            if r['warnings']:
                print(f"    Fila {r['fila']}: {', '.join(r['warnings'])}")


def validate_file(filepath, tipo, empresa):
    """Validate an Excel file and print report."""
    if tipo == 'mixto':
        xls = pd.ExcelFile(filepath)
        sheets = {
            name.lower().strip(): pd.read_excel(xls, sheet_name=name)
            for name in xls.sheet_names
        }
    else:
        df = pd.read_excel(filepath)
        sheets = {tipo: df}

    existing_rucs = set(
        Cliente.objects.filter(empresa=empresa).values_list('ruc', flat=True)
    )
    existing_skus = set(
        Producto.objects.filter(empresa=empresa).values_list('sku', flat=True)
    )
    existing_almacenes = set(
        Almacen.objects.filter(empresa=empresa).values_list('codigo', flat=True)
    )

    all_valid = True
    for sheet_name, df in sheets.items():
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
        results = []

        for idx, row in df.iterrows():
            row_num = idx + 2
            row_dict = row.to_dict()

            if sheet_name == 'clientes':
                result = validate_clientes_row(row_dict, row_num, existing_rucs)
            elif sheet_name == 'productos':
                result = validate_productos_row(row_dict, row_num, existing_skus)
            elif sheet_name == 'stock':
                result = validate_stock_row(row_dict, row_num, existing_skus, existing_almacenes)
            elif sheet_name == 'ventas':
                result = validate_ventas_row(row_dict, row_num, existing_rucs, existing_skus)
            else:
                print(f"  Hoja '{sheet_name}' no reconocida, se omite.")
                continue

            results.append(result.to_dict())

        print_report(sheet_name, results)
        if any(not r['valida'] for r in results):
            all_valid = False

    return all_valid


def main():
    parser = argparse.ArgumentParser(description='Importar datos desde Excel')
    parser.add_argument('--empresa', required=True, help='Código de la empresa')
    parser.add_argument('--file', required=True, help='Ruta al archivo Excel')
    parser.add_argument('--tipo', required=True,
                        choices=['clientes', 'productos', 'stock', 'ventas', 'mixto'],
                        help='Tipo de importación')
    parser.add_argument('--validar-solo', action='store_true',
                        help='Solo validar, no importar')
    parser.add_argument('--forzar', action='store_true',
                        help='Importar incluso con warnings')

    args = parser.parse_args()

    # Verify empresa exists
    try:
        empresa = Empresa.objects.get(codigo=args.empresa)
    except Empresa.DoesNotExist:
        print(f"Error: Empresa con código '{args.empresa}' no encontrada.")
        sys.exit(1)

    if not os.path.exists(args.file):
        print(f"Error: Archivo '{args.file}' no encontrado.")
        sys.exit(1)

    print(f"Empresa: {empresa.nombre} ({empresa.codigo})")
    print(f"Archivo: {args.file}")
    print(f"Tipo: {args.tipo}")

    # Phase 1: Validate
    print("\n--- FASE 1: VALIDACIÓN ---")
    is_valid = validate_file(args.file, args.tipo, empresa)

    if args.validar_solo:
        print("\n--- Solo validación solicitada. Fin. ---")
        sys.exit(0 if is_valid else 1)

    if not is_valid and not args.forzar:
        print("\n--- Se encontraron errores. Use --forzar para importar de todas formas. ---")
        sys.exit(1)

    # Phase 2: Import
    print("\n--- FASE 2: IMPORTACIÓN ---")
    confirm = input("¿Desea proceder con la importación? (s/n): ")
    if confirm.lower() != 's':
        print("Importación cancelada.")
        sys.exit(0)

    from apps.importacion.tasks import (
        _import_clientes, _import_productos, _import_stock, _import_ventas,
    )

    if args.tipo == 'mixto':
        xls = pd.ExcelFile(args.file)
        sheets = {
            name.lower().strip(): pd.read_excel(xls, sheet_name=name)
            for name in xls.sheet_names
        }
    else:
        df = pd.read_excel(args.file)
        sheets = {args.tipo: df}

    import_order = ['clientes', 'productos', 'stock', 'ventas']
    total_imported = 0
    total_errors = 0

    for sheet_name in import_order:
        if sheet_name not in sheets:
            continue
        df = sheets[sheet_name]
        df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]

        print(f"\n  Importando {sheet_name}...")
        if sheet_name == 'clientes':
            count, errs = _import_clientes(df, empresa)
        elif sheet_name == 'productos':
            count, errs = _import_productos(df, empresa)
        elif sheet_name == 'stock':
            count, errs = _import_stock(df, empresa)
        elif sheet_name == 'ventas':
            count, errs = _import_ventas(df, empresa)
        else:
            continue

        total_imported += count
        total_errors += len(errs)
        print(f"    Importados: {count}, Errores: {len(errs)}")
        for err in errs[:10]:
            print(f"      Fila {err['fila']}: {err['error']}")
        if len(errs) > 10:
            print(f"      ... y {len(errs) - 10} errores más.")

    print(f"\n{'='*60}")
    print(f"  RESUMEN FINAL")
    print(f"  Total importados: {total_imported}")
    print(f"  Total errores: {total_errors}")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()
