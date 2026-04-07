"""Command para importar productos con cuentas contables desde Excel."""
import os
import openpyxl
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.empresas.models import Empresa
from apps.productos.models import Producto
from apps.contabilidad.models import PlanCuentas


class Command(BaseCommand):
    help = 'Importar productos con cuentas contables desde Excel'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'archivo_excel',
            type=str,
            help='Ruta al archivo Excel con los productos'
        )
        parser.add_argument(
            '--empresa-id',
            type=str,
            help='ID de la empresa (si no se proporciona, usa la primera)'
        )
        parser.add_argument(
            '--cuenta-contable',
            type=str,
            help='Código de cuenta contable a asignar por defecto'
        )
    
    @transaction.atomic
    def handle(self, *args, **options):
        archivo = options['archivo_excel']
        empresa_id = options.get('empresa_id')
        cuenta_default = options.get('cuenta_contable')
        
        # Validar archivo
        if not os.path.exists(archivo):
            raise CommandError(f'Archivo no encontrado: {archivo}')
        
        # Obtener empresa
        if empresa_id:
            try:
                empresa = Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                raise CommandError(f'Empresa no encontrada: {empresa_id}')
        else:
            empresa = Empresa.objects.first()
            if not empresa:
                raise CommandError('No hay empresas en el sistema')
        
        self.stdout.write(f"📌 Importando productos para: {empresa.nombre}")
        
        # Cargar Excel
        try:
            wb = openpyxl.load_workbook(archivo)
            ws = wb.active
        except Exception as e:
            raise CommandError(f'Error al abrir Excel: {str(e)}')
        
        # Procesar filas (asumir header en fila 1)
        contador = 0
        errores = []
        cuenta_default_obj = None
        
        if cuenta_default:
            try:
                cuenta_default_obj = PlanCuentas.objects.get(
                    empresa=empresa,
                    codigo_cuenta=cuenta_default
                )
            except PlanCuentas.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠️  Cuenta por defecto no encontrada: {cuenta_default}"
                    )
                )
        
        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            try:
                # Columnas esperadas:
                # A: Código de Producto
                # B: Descripción
                # C: Categoría (opcional)
                # D: Precio Unitario
                # E: Stock Mínimo (opcional)
                # F: Stock Máximo (opcional)
                # G: Código Cuenta Contable (opcional)
                # H: Unidad de Medida (opcional)
                
                codigo = str(row[0]).strip() if row[0] else None
                descripcion = str(row[1]).strip() if row[1] else None
                categoria = str(row[2]).strip() if row[2] else ''
                precio_str = str(row[3]).strip() if row[3] else '0'
                stock_minimo_str = str(row[4]).strip() if row[4] else '0'
                stock_maximo_str = str(row[5]).strip() if row[5] else '0'
                codigo_cuenta = str(row[6]).strip() if row[6] else None
                unidad_medida = str(row[7]).strip() if row[7] else 'UN'
                
                # Validar campos requeridos
                if not codigo or not descripcion:
                    errores.append(f"Fila {idx}: Faltan código o descripción")
                    continue
                
                # Convertir valores numéricos
                try:
                    precio = Decimal(precio_str)
                    stock_minimo = int(float(stock_minimo_str))
                    stock_maximo = int(float(stock_maximo_str))
                except (ValueError, decimal.InvalidOperation):
                    errores.append(
                        f"Fila {idx}: Valores numéricos inválidos"
                    )
                    continue
                
                # Obtener cuenta contable
                cuenta = None
                if codigo_cuenta:
                    try:
                        cuenta = PlanCuentas.objects.get(
                            empresa=empresa,
                            codigo_cuenta=codigo_cuenta
                        )
                    except PlanCuentas.DoesNotExist:
                        errores.append(
                            f"Fila {idx}: Cuenta {codigo_cuenta} no encontrada"
                        )
                        continue
                elif cuenta_default_obj:
                    cuenta = cuenta_default_obj
                
                # Crear o actualizar producto
                producto, creada = Producto.objects.get_or_create(
                    empresa=empresa,
                    codigo=codigo,
                    defaults={
                        'descripcion': descripcion,
                        'categoria': categoria,
                        'precio_unitario': precio,
                        'stock_minimo': stock_minimo,
                        'stock_maximo': stock_maximo,
                        'unidad_medida': unidad_medida,
                        'cuenta_contable': cuenta,
                    }
                )
                
                if not creada:
                    producto.descripcion = descripcion
                    producto.categoria = categoria
                    producto.precio_unitario = precio
                    producto.stock_minimo = stock_minimo
                    producto.stock_maximo = stock_maximo
                    producto.unidad_medida = unidad_medida
                    if cuenta:
                        producto.cuenta_contable = cuenta
                    producto.save()
                
                contador += 1
                status = "🆕 CREADO" if creada else "♻️  ACTUALIZADO"
                cuenta_info = f" [{cuenta.codigo_cuenta}]" if cuenta else ""
                self.stdout.write(
                    f"  {status}: {codigo} - {descripcion[:40]}{cuenta_info}"
                )
                
            except Exception as e:
                errores.append(f"Fila {idx}: {str(e)}")
        
        # Resumen
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"✅ Proceso completado: {contador} productos importados")
        
        if errores:
            self.stdout.write(f"\n⚠️  {len(errores)} errores encontrados:")
            for error in errores[:10]:  # Mostrar máximo 10 errores
                self.stdout.write(f"  - {error}")
            if len(errores) > 10:
                self.stdout.write(f"  ... y {len(errores) - 10} más")
