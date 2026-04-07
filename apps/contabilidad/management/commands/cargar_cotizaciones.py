"""Command para cargar cotizaciones diarias desde Excel."""
import os
import openpyxl
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.empresas.models import Empresa
from apps.contabilidad.models import CotizacionDiaria
from apps.usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Cargar cotizaciones diarias desde archivo Excel'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'archivo_excel',
            type=str,
            help='Ruta al archivo Excel con las cotizaciones'
        )
        parser.add_argument(
            '--empresa-id',
            type=str,
            help='ID de la empresa (si no se proporciona, usa la primera)'
        )
        parser.add_argument(
            '--usuario-id',
            type=str,
            help='ID del usuario que carga (admin por defecto)'
        )
    
    @transaction.atomic
    def handle(self, *args, **options):
        archivo = options['archivo_excel']
        empresa_id = options.get('empresa_id')
        usuario_id = options.get('usuario_id')
        
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
        
        # Obtener usuario
        if usuario_id:
            try:
                usuario = Usuario.objects.get(id=usuario_id)
            except Usuario.DoesNotExist:
                raise CommandError(f'Usuario no encontrado: {usuario_id}')
        else:
            usuario = Usuario.objects.filter(is_superuser=True).first()
            if not usuario:
                raise CommandError('No hay usuarios administradores')
        
        self.stdout.write(f"📌 Cargando cotizaciones para: {empresa.nombre}")
        self.stdout.write(f"   Usuario: {usuario.username}")
        
        # Cargar Excel
        try:
            wb = openpyxl.load_workbook(archivo)
            ws = wb.active
        except Exception as e:
            raise CommandError(f'Error al abrir Excel: {str(e)}')
        
        # Procesar filas (asumir header en fila 1)
        contador = 0
        errores = []
        
        for idx, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
            try:
                # Columnas esperadas:
                # A: Fecha (YYYY-MM-DD o datetime)
                # B: Moneda Origen (USD, PYG, EUR, etc)
                # C: Moneda Destino (USD, PYG, EUR, etc)
                # D: Tasa (decimal)
                # E: Fuente (opcional)
                
                fecha_raw = row[0]
                moneda_origen = str(row[1]).upper().strip() if row[1] else 'USD'
                moneda_destino = str(row[2]).upper().strip() if row[2] else 'PYG'
                tasa_str = str(row[3]).strip() if row[3] else '0'
                fuente = str(row[4]).strip() if row[4] else 'Manual'
                
                # Parsear fecha
                if isinstance(fecha_raw, datetime):
                    fecha = fecha_raw.date()
                else:
                    try:
                        fecha = datetime.strptime(
                            str(fecha_raw).strip(), '%Y-%m-%d'
                        ).date()
                    except ValueError:
                        errores.append(f"Fila {idx}: Formato de fecha inválido: {fecha_raw}")
                        continue
                
                # Convertir tasa
                try:
                    tasa = Decimal(tasa_str)
                    if tasa <= 0:
                        raise ValueError("Tasa debe ser positiva")
                except (ValueError, Exception) as e:
                    errores.append(f"Fila {idx}: Tasa inválida: {tasa_str} - {str(e)}")
                    continue
                
                # Validar monedas
                monedas_validas = ['USD', 'PYG', 'EUR', 'ARS', 'BRL']
                if moneda_origen not in monedas_validas:
                    errores.append(
                        f"Fila {idx}: Moneda origen inválida: {moneda_origen}"
                    )
                    continue
                if moneda_destino not in monedas_validas:
                    errores.append(
                        f"Fila {idx}: Moneda destino inválida: {moneda_destino}"
                    )
                    continue
                
                # Crear o actualizar cotización
                cotizacion, creada = CotizacionDiaria.objects.get_or_create(
                    empresa=empresa,
                    fecha=fecha,
                    moneda_origen=moneda_origen,
                    moneda_destino=moneda_destino,
                    defaults={
                        'tasa': tasa,
                        'fuente': fuente,
                        'usuario_carga': usuario,
                    }
                )
                
                if not creada:
                    cotizacion.tasa = tasa
                    cotizacion.fuente = fuente
                    cotizacion.usuario_carga = usuario
                    cotizacion.save()
                
                contador += 1
                status = "🆕 CREADA" if creada else "♻️  ACTUALIZADA"
                self.stdout.write(
                    f"  {status}: {fecha} - {moneda_origen}/{moneda_destino} = {tasa}"
                )
                
            except Exception as e:
                errores.append(f"Fila {idx}: {str(e)}")
        
        # Resumen
        self.stdout.write("\n" + "="*60)
        self.stdout.write(
            f"✅ Proceso completado: {contador} cotizaciones cargadas"
        )
        
        if errores:
            self.stdout.write(f"\n⚠️  {len(errores)} errores encontrados:")
            for error in errores[:10]:  # Mostrar máximo 10 errores
                self.stdout.write(f"  - {error}")
            if len(errores) > 10:
                self.stdout.write(f"  ... y {len(errores) - 10} más")
