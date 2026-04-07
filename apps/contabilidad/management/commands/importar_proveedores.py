"""Command para importar proveedores desde Excel."""
import os
import openpyxl
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.empresas.models import Empresa
from apps.compras.models import Proveedor
from apps.contabilidad.models import PlanCuentas


class Command(BaseCommand):
    help = 'Importar proveedores desde archivo Excel'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'archivo_excel',
            type=str,
            help='Ruta al archivo Excel con los proveedores'
        )
        parser.add_argument(
            '--empresa-id',
            type=str,
            help='ID de la empresa (si no se proporciona, usa la primera)'
        )
        parser.add_argument(
            '--cuenta-contable',
            type=str,
            help='Código de cuenta contable a asignar (si no está en Excel)'
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
        
        self.stdout.write(f"📌 Importando proveedores para: {empresa.nombre}")
        
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
                # A: Nombre Proveedor
                # B: RUC
                # C: Email
                # D: Teléfono
                # E: Dirección
                # F: Email SET (opcional)
                # G: Emite Electrónica (S/N) (opcional)
                # H: Timbrado Número (opcional)
                # I: Timbrado Vencimiento (opcional)
                # J: Código Cuenta Contable (opcional)
                
                nombre = str(row[0]).strip() if row[0] else None
                ruc = str(row[1]).strip() if row[1] else None
                email = str(row[2]).strip() if row[2] else ''
                telefono = str(row[3]).strip() if row[3] else ''
                direccion = str(row[4]).strip() if row[4] else ''
                email_set = str(row[5]).strip() if row[5] else ''
                emite_electronica = str(row[6]).upper() == 'S' if row[6] else False
                timbrado_numero = str(row[7]).strip() if row[7] else ''
                timbrado_vencimiento = row[8] if row[8] else None
                codigo_cuenta = str(row[9]).strip() if row[9] else None
                
                # Validar campos requeridos
                if not nombre or not ruc:
                    errores.append(f"Fila {idx}: Faltan nombre o RUC")
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
                
                # Crear o actualizar proveedor
                proveedor, creada = Proveedor.objects.get_or_create(
                    empresa=empresa,
                    ruc_numero=ruc,
                    defaults={
                        'nombre': nombre,
                        'email': email,
                        'telefono': telefono,
                        'direccion': direccion,
                        'email_set': email_set,
                        'emite_electronica': emite_electronica,
                        'timbrado_numero': timbrado_numero,
                        'timbrado_vencimiento': timbrado_vencimiento,
                        'cuenta_contable': cuenta,
                    }
                )
                
                if not creada:
                    proveedor.nombre = nombre
                    proveedor.email = email
                    proveedor.telefono = telefono
                    proveedor.direccion = direccion
                    proveedor.email_set = email_set
                    proveedor.emite_electronica = emite_electronica
                    proveedor.timbrado_numero = timbrado_numero
                    if timbrado_vencimiento:
                        proveedor.timbrado_vencimiento = timbrado_vencimiento
                    if cuenta:
                        proveedor.cuenta_contable = cuenta
                    proveedor.save()
                
                contador += 1
                status = "🆕 CREADO" if creada else "♻️  ACTUALIZADO"
                cuenta_info = f" [{cuenta.codigo_cuenta}]" if cuenta else ""
                self.stdout.write(
                    f"  {status}: {nombre} (RUC: {ruc}){cuenta_info}"
                )
                
            except Exception as e:
                errores.append(f"Fila {idx}: {str(e)}")
        
        # Resumen
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"✅ Proceso completado: {contador} proveedores importados")
        
        if errores:
            self.stdout.write(f"\n⚠️  {len(errores)} errores encontrados:")
            for error in errores[:10]:  # Mostrar máximo 10 errores
                self.stdout.write(f"  - {error}")
            if len(errores) > 10:
                self.stdout.write(f"  ... y {len(errores) - 10} más")
