"""Celery tasks for Excel import processing."""
import logging
from datetime import datetime
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from celery import shared_task

import pandas as pd

logger = logging.getLogger('apps.importacion')


@shared_task(bind=True, max_retries=1)
def validate_import_task(self, job_id):
    """Pre-validate an uploaded Excel file without importing."""
    from .models import ImportJob
    from .validators import (
        validate_clientes_row, validate_productos_row,
        validate_stock_row, validate_ventas_row,
    )

    job = ImportJob.objects.get(id=job_id)
    job.estado = 'validando'
    job.task_id = self.request.id or ''
    job.iniciado_en = timezone.now()
    job.save(update_fields=['estado', 'task_id', 'iniciado_en'])

    try:
        filepath = job.archivo.path
        tipo = job.tipo
        empresa = job.empresa

        # Read the Excel file
        if tipo == 'mixto':
            xls = pd.ExcelFile(filepath)
            sheets = {name.lower().strip(): pd.read_excel(xls, sheet_name=name)
                      for name in xls.sheet_names}
        else:
            df = pd.read_excel(filepath)
            sheets = {tipo: df}

        reporte = {}
        total_filas = 0
        total_validas = 0
        total_warnings = 0
        total_errores = 0

        # Pre-fetch existing data for reference validation
        from apps.clientes.models import Cliente
        from apps.productos.models import Producto
        from apps.inventario.models import Almacen

        existing_rucs = set(
            Cliente.objects.filter(empresa=empresa).values_list('ruc', flat=True)
        )
        existing_skus = set(
            Producto.objects.filter(empresa=empresa).values_list('sku', flat=True)
        )
        existing_almacenes = set(
            Almacen.objects.filter(empresa=empresa).values_list('codigo', flat=True)
        )

        for sheet_name, df in sheets.items():
            df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
            rows_results = []

            for idx, row in df.iterrows():
                row_num = idx + 2  # Excel row (1-indexed + header)
                row_dict = row.to_dict()

                if sheet_name == 'clientes':
                    result = validate_clientes_row(row_dict, row_num, existing_rucs)
                elif sheet_name == 'productos':
                    result = validate_productos_row(row_dict, row_num, existing_skus)
                elif sheet_name == 'stock':
                    result = validate_stock_row(
                        row_dict, row_num, existing_skus, existing_almacenes
                    )
                elif sheet_name == 'ventas':
                    result = validate_ventas_row(
                        row_dict, row_num, existing_rucs, existing_skus
                    )
                else:
                    continue

                rows_results.append(result.to_dict())
                total_filas += 1
                if result.is_valid:
                    total_validas += 1
                    if result.has_warnings:
                        total_warnings += 1
                else:
                    total_errores += 1

            reporte[sheet_name] = {
                'total_filas': len(df),
                'filas_validas': sum(1 for r in rows_results if r['valida']),
                'filas_errores': sum(1 for r in rows_results if not r['valida']),
                'filas_warnings': sum(1 for r in rows_results if r['warnings']),
                'detalle': rows_results[:500],  # Limit detail for large files
            }

        job.estado = 'validado'
        job.total_filas = total_filas
        job.filas_validas = total_validas
        job.filas_warnings = total_warnings
        job.filas_errores = total_errores
        job.reporte_validacion = reporte
        job.finalizado_en = timezone.now()
        job.mensaje = f"Validación completa: {total_validas} válidas, {total_errores} errores, {total_warnings} warnings"
        job.save()

        return {
            'job_id': str(job.id),
            'estado': 'validado',
            'total_filas': total_filas,
            'filas_validas': total_validas,
            'filas_errores': total_errores,
        }

    except Exception as e:
        logger.error(f"Error validating import job {job_id}: {e}", exc_info=True)
        job.estado = 'error'
        job.mensaje = str(e)[:1000]
        job.finalizado_en = timezone.now()
        job.save(update_fields=['estado', 'mensaje', 'finalizado_en'])
        raise


@shared_task(bind=True, max_retries=0)
def execute_import_task(self, job_id):
    """Execute the actual import after validation has been confirmed."""
    from .models import ImportJob

    job = ImportJob.objects.get(id=job_id)
    if job.estado != 'validado':
        job.mensaje = "El trabajo debe estar validado antes de importar."
        job.save(update_fields=['mensaje'])
        return {'error': job.mensaje}

    job.estado = 'importando'
    job.task_id = self.request.id or ''
    job.iniciado_en = timezone.now()
    job.save(update_fields=['estado', 'task_id', 'iniciado_en'])

    try:
        filepath = job.archivo.path
        tipo = job.tipo
        empresa = job.empresa

        if tipo == 'mixto':
            xls = pd.ExcelFile(filepath)
            sheets = {name.lower().strip(): pd.read_excel(xls, sheet_name=name)
                      for name in xls.sheet_names}
        else:
            df = pd.read_excel(filepath)
            sheets = {tipo: df}

        total_imported = 0
        errors = []

        # Import order matters: clientes -> productos -> stock -> ventas
        import_order = ['clientes', 'productos', 'stock', 'ventas']
        for sheet_name in import_order:
            if sheet_name not in sheets:
                continue
            df = sheets[sheet_name]
            df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]

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
            errors.extend(errs)

        job.estado = 'completado'
        job.filas_importadas = total_imported
        job.reporte_errores = errors[:1000] if errors else None
        job.finalizado_en = timezone.now()
        job.mensaje = f"Importación completa: {total_imported} registros importados, {len(errors)} errores"
        job.save()

        return {
            'job_id': str(job.id),
            'estado': 'completado',
            'importados': total_imported,
            'errores': len(errors),
        }

    except Exception as e:
        logger.error(f"Error executing import job {job_id}: {e}", exc_info=True)
        job.estado = 'error'
        job.mensaje = str(e)[:1000]
        job.finalizado_en = timezone.now()
        job.save(update_fields=['estado', 'mensaje', 'finalizado_en'])
        raise


def _import_clientes(df, empresa):
    """Bulk import clientes from DataFrame."""
    from apps.clientes.models import Cliente

    imported = 0
    errors = []
    batch = []
    BATCH_SIZE = 500

    existing_rucs = set(
        Cliente.objects.filter(empresa=empresa).values_list('ruc', flat=True)
    )

    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            ruc = str(row.get('ruc', '')).strip()
            if not ruc or ruc in existing_rucs:
                if ruc in existing_rucs:
                    errors.append({
                        'fila': row_num, 'hoja': 'clientes',
                        'error': f'RUC duplicado: {ruc} - se omite'
                    })
                continue

            nombre = str(row.get('nombre', '')).strip()
            if not nombre:
                errors.append({
                    'fila': row_num, 'hoja': 'clientes',
                    'error': 'nombre vacío'
                })
                continue

            cliente = Cliente(
                empresa=empresa,
                nombre=nombre,
                ruc=ruc,
                telefono=str(row.get('telefono', '')).strip() if pd.notna(row.get('telefono')) else '',
                email=str(row.get('email', '')).strip() if pd.notna(row.get('email')) else '',
                direccion_facturacion=str(row.get('direccion_facturacion', '')).strip() if pd.notna(row.get('direccion_facturacion')) else '',
                direccion_entrega=str(row.get('direccion_entrega', '')).strip() if pd.notna(row.get('direccion_entrega')) else '',
                tipo_cliente=str(row.get('tipo_cliente', 'persona')).strip() if pd.notna(row.get('tipo_cliente')) else 'persona',
                sector=str(row.get('sector', '')).strip() if pd.notna(row.get('sector')) else '',
                zona=str(row.get('zona', '')).strip() if pd.notna(row.get('zona')) else '',
                observaciones=str(row.get('observaciones', '')).strip() if pd.notna(row.get('observaciones')) else '',
            )
            batch.append(cliente)
            existing_rucs.add(ruc)

            if len(batch) >= BATCH_SIZE:
                with transaction.atomic():
                    Cliente.objects.bulk_create(batch, ignore_conflicts=True)
                imported += len(batch)
                batch = []

        except Exception as e:
            errors.append({'fila': row_num, 'hoja': 'clientes', 'error': str(e)})

    if batch:
        with transaction.atomic():
            Cliente.objects.bulk_create(batch, ignore_conflicts=True)
        imported += len(batch)

    return imported, errors


def _import_productos(df, empresa):
    """Bulk import productos from DataFrame."""
    from apps.productos.models import Producto, Categoria

    imported = 0
    errors = []
    batch = []
    BATCH_SIZE = 500

    existing_skus = set(
        Producto.objects.filter(empresa=empresa).values_list('sku', flat=True)
    )
    # Cache categories
    cat_cache = {}

    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            sku = str(row.get('sku', '')).strip()
            if not sku or sku in existing_skus:
                if sku in existing_skus:
                    errors.append({
                        'fila': row_num, 'hoja': 'productos',
                        'error': f'SKU duplicado: {sku} - se omite'
                    })
                continue

            nombre = str(row.get('nombre', '')).strip()
            if not nombre:
                errors.append({
                    'fila': row_num, 'hoja': 'productos',
                    'error': 'nombre vacío'
                })
                continue

            try:
                raw_precio = row.get('precio_unitario', 0)
                precio = Decimal(str(raw_precio).replace(',', '.')) if pd.notna(raw_precio) else Decimal('0')
                if not precio.is_finite():
                    precio = Decimal('0')
            except Exception:
                precio = Decimal('0')

            try:
                raw_costo = row.get('costo', 0)
                costo = Decimal(str(raw_costo).replace(',', '.')) if pd.notna(raw_costo) else Decimal('0')
                if not costo.is_finite():
                    costo = Decimal('0')
            except Exception:
                costo = Decimal('0')

            # Handle category
            categoria_obj = None
            cat_name = str(row.get('categoria', '')).strip() if pd.notna(row.get('categoria')) else ''
            if cat_name:
                if cat_name not in cat_cache:
                    cat_obj, _ = Categoria.objects.get_or_create(
                        empresa=empresa, nombre=cat_name,
                        defaults={'descripcion': ''}
                    )
                    cat_cache[cat_name] = cat_obj
                categoria_obj = cat_cache[cat_name]

            producto = Producto(
                empresa=empresa,
                sku=sku,
                nombre=nombre,
                descripcion=str(row.get('descripcion', '')).strip() if pd.notna(row.get('descripcion')) else '',
                categoria=categoria_obj,
                precio_unitario=precio,
                costo=costo,
                imagen_url=str(row.get('imagen_url', '')).strip() if pd.notna(row.get('imagen_url')) else '',
            )
            batch.append(producto)
            existing_skus.add(sku)

            if len(batch) >= BATCH_SIZE:
                with transaction.atomic():
                    Producto.objects.bulk_create(batch, ignore_conflicts=True)
                imported += len(batch)
                batch = []

        except Exception as e:
            errors.append({'fila': row_num, 'hoja': 'productos', 'error': str(e)})

    if batch:
        with transaction.atomic():
            Producto.objects.bulk_create(batch, ignore_conflicts=True)
        imported += len(batch)

    return imported, errors


def _import_stock(df, empresa):
    """Bulk import stock from DataFrame."""
    from apps.productos.models import Producto
    from apps.inventario.models import Almacen, Stock

    imported = 0
    errors = []
    BATCH_SIZE = 500

    # Build lookup maps
    sku_map = dict(
        Producto.objects.filter(empresa=empresa).values_list('sku', 'id')
    )
    almacen_map = dict(
        Almacen.objects.filter(empresa=empresa).values_list('codigo', 'id')
    )

    batch = []
    for idx, row in df.iterrows():
        row_num = idx + 2
        try:
            sku = str(row.get('sku', '')).strip()
            almacen_codigo = str(row.get('almacen_codigo', '')).strip()

            if sku not in sku_map:
                errors.append({
                    'fila': row_num, 'hoja': 'stock',
                    'error': f'SKU no encontrado: {sku}'
                })
                continue

            if almacen_codigo not in almacen_map:
                # Auto-create almacen
                almacen_obj = Almacen.objects.create(
                    empresa=empresa, codigo=almacen_codigo,
                    nombre=f'Almacén {almacen_codigo}'
                )
                almacen_map[almacen_codigo] = almacen_obj.id

            try:
                raw_cant = row.get('cantidad', 0)
                cantidad = Decimal(str(raw_cant).replace(',', '.')) if pd.notna(raw_cant) else Decimal('0')
                if not cantidad.is_finite():
                    cantidad = Decimal('0')
            except Exception:
                cantidad = Decimal('0')

            ubicacion = str(row.get('ubicacion', '')).strip() if pd.notna(row.get('ubicacion')) else ''

            stock, created = Stock.objects.update_or_create(
                empresa=empresa,
                producto_id=sku_map[sku],
                almacen_id=almacen_map[almacen_codigo],
                defaults={
                    'cantidad': cantidad,
                    'ubicacion': ubicacion,
                }
            )
            imported += 1

        except Exception as e:
            errors.append({'fila': row_num, 'hoja': 'stock', 'error': str(e)})

    return imported, errors


def _import_ventas(df, empresa):
    """Import ventas from DataFrame. Groups lines by numero."""
    from apps.clientes.models import Cliente
    from apps.productos.models import Producto
    from apps.ventas.models import Venta, LineaVenta

    imported = 0
    errors = []

    ruc_map = dict(
        Cliente.objects.filter(empresa=empresa).values_list('ruc', 'id')
    )
    sku_map = dict(
        Producto.objects.filter(empresa=empresa).values_list('sku', 'id')
    )
    existing_numeros = set(
        Venta.objects.filter(empresa=empresa).values_list('numero', flat=True)
    )

    # Group rows by numero
    ventas_grouped = {}
    for idx, row in df.iterrows():
        row_num = idx + 2
        numero = str(row.get('numero', '')).strip()
        if not numero:
            errors.append({'fila': row_num, 'hoja': 'ventas', 'error': 'numero vacío'})
            continue
        if numero not in ventas_grouped:
            ventas_grouped[numero] = []
        ventas_grouped[numero].append((row_num, row))

    for numero, rows in ventas_grouped.items():
        if numero in existing_numeros:
            errors.append({
                'fila': rows[0][0], 'hoja': 'ventas',
                'error': f'Venta número duplicado: {numero}'
            })
            continue

        first_row_num, first_row = rows[0]
        cliente_ruc = str(first_row.get('cliente_ruc', '')).strip()
        if cliente_ruc not in ruc_map:
            errors.append({
                'fila': first_row_num, 'hoja': 'ventas',
                'error': f'Cliente RUC no encontrado: {cliente_ruc}'
            })
            continue

        try:
            fecha_val = first_row.get('fecha')
            if isinstance(fecha_val, datetime):
                fecha = fecha_val.date()
            else:
                fecha = pd.to_datetime(str(fecha_val)).date()
        except Exception:
            errors.append({
                'fila': first_row_num, 'hoja': 'ventas',
                'error': f'Fecha inválida: {first_row.get("fecha")}'
            })
            continue

        estado = str(first_row.get('estado', 'confirmada')).strip() if pd.notna(first_row.get('estado')) else 'confirmada'
        metodo_pago = str(first_row.get('metodo_pago', '')).strip() if pd.notna(first_row.get('metodo_pago')) else ''

        try:
            with transaction.atomic():
                venta = Venta.objects.create(
                    empresa=empresa,
                    numero=numero,
                    cliente_id=ruc_map[cliente_ruc],
                    fecha=fecha,
                    estado=estado,
                    metodo_pago=metodo_pago,
                )

                lineas_batch = []
                for row_num, row in rows:
                    sku = str(row.get('sku', '')).strip()
                    if sku not in sku_map:
                        errors.append({
                            'fila': row_num, 'hoja': 'ventas',
                            'error': f'SKU no encontrado: {sku}'
                        })
                        continue

                    try:
                        raw_c = row.get('cantidad', 0)
                        raw_p = row.get('precio_unitario', 0)
                        raw_i = row.get('impuestos', 10)
                        cantidad = Decimal(str(raw_c).replace(',', '.')) if pd.notna(raw_c) else Decimal('0')
                        precio = Decimal(str(raw_p).replace(',', '.')) if pd.notna(raw_p) else Decimal('0')
                        imp_pct = Decimal(str(raw_i).replace(',', '.')) if pd.notna(raw_i) else Decimal('10')
                        for val in (cantidad, precio, imp_pct):
                            if not val.is_finite():
                                raise ValueError('NaN value')
                    except Exception:
                        errors.append({
                            'fila': row_num, 'hoja': 'ventas',
                            'error': 'Valores numéricos inválidos'
                        })
                        continue

                    lineas_batch.append(LineaVenta(
                        venta=venta,
                        producto_id=sku_map[sku],
                        cantidad=cantidad,
                        precio_unitario=precio,
                        impuesto_porcentaje=imp_pct,
                    ))

                # Save lines (triggers subtotal calc in save())
                for linea in lineas_batch:
                    linea.save()

                venta.recalcular_totales()
                existing_numeros.add(numero)
                imported += 1

        except Exception as e:
            errors.append({
                'fila': first_row_num, 'hoja': 'ventas',
                'error': f'Error creando venta {numero}: {str(e)}'
            })

    return imported, errors
