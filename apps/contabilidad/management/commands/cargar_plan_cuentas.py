"""Command para cargar plan de cuentas desde Excel."""
import os
import openpyxl
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.empresas.models import Empresa
from apps.contabilidad.models import PlanCuentas


class Command(BaseCommand):
    help = 'Cargar plan de cuentas desde archivo Excel'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'archivo_excel',
            type=str,
            help='Ruta al archivo Excel con el plan de cuentas'
        )
        parser.add_argument(
            '--empresa-id',
            type=str,
            help='ID de la empresa (si no se proporciona, usa la primera)'
        )
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Limpiar todas las cuentas existentes antes de cargar'
        )
    
    @transaction.atomic
    def handle(self, *args, **options):
        archivo = options['archivo_excel']
        empresa_id = options.get('empresa_id')
        limpiar = options.get('limpiar', False)
        
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
        
        self.stdout.write(f"📌 Cargando plan de cuentas para: {empresa.nombre}")
        
        # Limpiar si se pide
        if limpiar:
            count = PlanCuentas.objects.filter(empresa=empresa).delete()[0]
            self.stdout.write(f"🗑️  Eliminadas {count} cuentas existentes")
        
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
                # A: Código de cuenta
                # B: Descripción
                # C: Condición (deudora/acreedora)
                # D: Clase (sintetica/analitica)
                # E: Código reducido
                # F: Acepta Ítem (S/N)
                # G: Acepta CC (S/N)
                # H: Acepta Nivel (S/N)
                
                codigo = str(row[0]).strip() if row[0] else None
                descripcion = str(row[1]).strip() if row[1] else None
                condicion = str(row[2]).strip().lower() if row[2] else 'deudora'
                clase = str(row[3]).strip().lower() if row[3] else 'analitica'
                codigo_reducido = str(row[4]).strip() if row[4] else ''
                acepta_item = str(row[5]).upper() == 'S' if row[5] else False
                acepta_cc = str(row[6]).upper() == 'S' if row[6] else False
                acepta_nivel = str(row[7]).upper() == 'S' if row[7] else False
                
                # Validar campos requeridos
                if not codigo or not descripcion:
                    errores.append(f"Fila {idx}: Faltan código o descripción")
                    continue
                
                # Mapear valores
                if condicion not in ['deudora', 'acreedora']:
                    condicion = 'deudora'
                
                if clase not in ['sintetica', 'analitica']:
                    clase = 'analitica'
                
                # Crear o actualizar cuenta
                cuenta, creada = PlanCuentas.objects.get_or_create(
                    empresa=empresa,
                    codigo_cuenta=codigo,
                    defaults={
                        'descripcion': descripcion,
                        'condicion': condicion,
                        'clase': clase,
                        'codigo_reducido': codigo_reducido,
                        'acepta_item': acepta_item,
                        'acepta_centro_costo': acepta_cc,
                        'acepta_nivel': acepta_nivel,
                    }
                )
                
                if not creada:
                    cuenta.descripcion = descripcion
                    cuenta.condicion = condicion
                    cuenta.clase = clase
                    cuenta.codigo_reducido = codigo_reducido
                    cuenta.acepta_item = acepta_item
                    cuenta.acepta_centro_costo = acepta_cc
                    cuenta.acepta_nivel = acepta_nivel
                    cuenta.save()
                
                contador += 1
                status = "🆕 CREADA" if creada else "♻️  ACTUALIZADA"
                self.stdout.write(f"  {status}: {codigo} - {descripcion[:40]}")
                
            except Exception as e:
                errores.append(f"Fila {idx}: {str(e)}")
        
        # Resumen
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"✅ Proceso completado: {contador} cuentas cargadas")
        
        if errores:
            self.stdout.write(f"\n⚠️  {len(errores)} errores encontrados:")
            for error in errores[:10]:  # Mostrar máximo 10 errores
                self.stdout.write(f"  - {error}")
            if len(errores) > 10:
                self.stdout.write(f"  ... y {len(errores) - 10} más")
