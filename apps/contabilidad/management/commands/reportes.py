"""Command para generar reportes contables."""
import csv
from datetime import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Sum, Q, F

from apps.empresas.models import Empresa
from apps.contabilidad.models import PlanCuentas, Asiento, LineaAsiento


class Command(BaseCommand):
    help = 'Generar reportes contables (Balance General, Mayor, Diario)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'tipo_reporte',
            type=str,
            choices=['balance', 'mayor', 'diario'],
            help='Tipo de reporte: balance, mayor, diario'
        )
        parser.add_argument(
            '--empresa-id',
            type=str,
            required=True,
            help='ID de la empresa'
        )
        parser.add_argument(
            '--desde',
            type=str,
            help='Fecha desde (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--hasta',
            type=str,
            help='Fecha hasta (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--salida',
            type=str,
            help='Archivo de salida (CSV). Si no se proporciona, imprime en pantalla'
        )
    
    def handle(self, *args, **options):
        tipo_reporte = options['tipo_reporte']
        empresa_id = options['empresa_id']
        desde_str = options.get('desde')
        hasta_str = options.get('hasta')
        salida = options.get('salida')
        
        # Obtener empresa
        try:
            empresa = Empresa.objects.get(id=empresa_id)
        except Empresa.DoesNotExist:
            raise CommandError(f'Empresa no encontrada: {empresa_id}')
        
        # Parsear fechas
        desde = None
        hasta = None
        if desde_str:
            try:
                desde = datetime.strptime(desde_str, '%Y-%m-%d').date()
            except ValueError:
                raise CommandError(f'Formato de fecha inválido: {desde_str}')
        
        if hasta_str:
            try:
                hasta = datetime.strptime(hasta_str, '%Y-%m-%d').date()
            except ValueError:
                raise CommandError(f'Formato de fecha inválido: {hasta_str}')
        
        self.stdout.write(f"📊 Generando reporte: {tipo_reporte.upper()}")
        self.stdout.write(f"   Empresa: {empresa.nombre}")
        
        if tipo_reporte == 'balance':
            datos = self._generar_balance_general(empresa)
        elif tipo_reporte == 'mayor':
            datos = self._generar_mayor(empresa, desde, hasta)
        elif tipo_reporte == 'diario':
            datos = self._generar_diario(empresa, desde, hasta)
        
        # Salida
        if salida:
            self._guardar_csv(datos, salida)
        else:
            self._imprimir_pantalla(datos)
    
    def _generar_balance_general(self, empresa):
        """Generar Balance General."""
        resultados = {
            'titulo': 'BALANCE GENERAL',
            'empresa': empresa.nombre,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'headers': ['Código', 'Descripción', 'Debe', 'Haber', 'Saldo'],
            'filas': [],
            'resumen': {}
        }
        
        # Obtener asientos registrados
        asientos = Asiento.objects.filter(
            empresa=empresa,
            estado='registrado'
        ).select_related()
        
        # Agrupar por cuenta
        cuentas = {}
        for asiento in asientos:
            for linea in asiento.lineas.all():
                cuenta_id = linea.cuenta.id
                if cuenta_id not in cuentas:
                    cuentas[cuenta_id] = {
                        'codigo': linea.cuenta.codigo_cuenta,
                        'descripcion': linea.cuenta.descripcion,
                        'debe': Decimal('0'),
                        'haber': Decimal('0'),
                        'condicion': linea.cuenta.condicion,
                    }
                cuentas[cuenta_id]['debe'] += linea.debe
                cuentas[cuenta_id]['haber'] += linea.haber
        
        # Calcular saldos por condición
        activos = {'debe': Decimal('0'), 'haber': Decimal('0')}
        pasivos = {'debe': Decimal('0'), 'haber': Decimal('0')}
        patrimonio = {'debe': Decimal('0'), 'haber': Decimal('0')}
        
        for cuenta_id, datos in cuentas.items():
            saldo = datos['debe'] - datos['haber']
            condicion = datos['condicion']
            
            resultados['filas'].append({
                'codigo': datos['codigo'],
                'descripcion': datos['descripcion'],
                'debe': datos['debe'],
                'haber': datos['haber'],
                'saldo': saldo,
            })
            
            # Clasificar
            if condicion == 'deudora':
                activos['debe'] += datos['debe']
                activos['haber'] += datos['haber']
            elif condicion == 'acreedora':
                pasivos['debe'] += datos['debe']
                pasivos['haber'] += datos['haber']
        
        resultados['resumen'] = {
            'activos': activos['debe'] - activos['haber'],
            'pasivos': pasivos['haber'] - pasivos['debe'],
            'patrimonio': patrimonio['haber'] - patrimonio['debe'],
        }
        
        return resultados
    
    def _generar_mayor(self, empresa, desde=None, hasta=None):
        """Generar Libro Mayor por cuenta."""
        resultados = {
            'titulo': 'LIBRO MAYOR',
            'empresa': empresa.nombre,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'periodos': {'desde': desde, 'hasta': hasta},
            'headers': ['Fecha', 'Asiento', 'Concepto', 'Debe', 'Haber', 'Saldo'],
            'mayores': []
        }
        
        # Obtener asientos
        asientos_qs = Asiento.objects.filter(
            empresa=empresa,
            estado='registrado'
        )
        
        if desde:
            asientos_qs = asientos_qs.filter(fecha_asiento__gte=desde)
        if hasta:
            asientos_qs = asientos_qs.filter(fecha_asiento__lte=hasta)
        
        # Agrupar por cuenta
        cuentas_mayor = {}
        for asiento in asientos_qs:
            for linea in asiento.lineas.all():
                cuenta_id = linea.cuenta.id
                if cuenta_id not in cuentas_mayor:
                    cuentas_mayor[cuenta_id] = {
                        'codigo': linea.cuenta.codigo_cuenta,
                        'descripcion': linea.cuenta.descripcion,
                        'movimientos': [],
                        'saldo': Decimal('0'),
                    }
                
                saldo = cuentas_mayor[cuenta_id]['saldo']
                saldo += linea.debe - linea.haber
                
                cuentas_mayor[cuenta_id]['movimientos'].append({
                    'fecha': asiento.fecha_asiento,
                    'numero': asiento.numero_asiento,
                    'concepto': linea.observacion or '',
                    'debe': linea.debe,
                    'haber': linea.haber,
                    'saldo': saldo,
                })
                cuentas_mayor[cuenta_id]['saldo'] = saldo
        
        resultados['mayores'] = list(cuentas_mayor.values())
        return resultados
    
    def _generar_diario(self, empresa, desde=None, hasta=None):
        """Generar Libro Diario."""
        resultados = {
            'titulo': 'LIBRO DIARIO',
            'empresa': empresa.nombre,
            'fecha': datetime.now().strftime('%Y-%m-%d'),
            'periodos': {'desde': desde, 'hasta': hasta},
            'headers': ['Fecha', 'Asiento', 'Código Cuenta', 'Descripción', 'Debe', 'Haber', 'Concepto'],
            'filas': [],
            'totales': {'debe': Decimal('0'), 'haber': Decimal('0')}
        }
        
        # Obtener asientos
        asientos_qs = Asiento.objects.filter(
            empresa=empresa,
            estado='registrado'
        ).order_by('fecha_asiento', 'numero_asiento')
        
        if desde:
            asientos_qs = asientos_qs.filter(fecha_asiento__gte=desde)
        if hasta:
            asientos_qs = asientos_qs.filter(fecha_asiento__lte=hasta)
        
        for asiento in asientos_qs:
            for linea in asiento.lineas.all():
                resultados['filas'].append({
                    'fecha': asiento.fecha_asiento,
                    'numero': asiento.numero_asiento,
                    'codigo': linea.cuenta.codigo_cuenta,
                    'descripcion': linea.cuenta.descripcion,
                    'debe': linea.debe,
                    'haber': linea.haber,
                    'concepto': linea.observacion or '',
                })
                resultados['totales']['debe'] += linea.debe
                resultados['totales']['haber'] += linea.haber
        
        return resultados
    
    def _guardar_csv(self, datos, ruta):
        """Guardar reporte en CSV."""
        try:
            with open(ruta, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Header
                writer.writerow([datos['titulo']])
                writer.writerow(['Empresa:', datos['empresa']])
                writer.writerow(['Fecha:', datos['fecha']])
                writer.writerow([])
                
                # Headers de columnas
                writer.writerow(datos['headers'])
                
                # Filas
                if 'filas' in datos:
                    for fila in datos['filas']:
                        row = [
                            fila.get('codigo', ''),
                            fila.get('descripcion', ''),
                            fila.get('debe', ''),
                            fila.get('haber', ''),
                            fila.get('saldo', ''),
                        ]
                        writer.writerow(row)
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Reporte guardado: {ruta}')
            )
        except Exception as e:
            raise CommandError(f'Error al guardar archivo: {str(e)}')
    
    def _imprimir_pantalla(self, datos):
        """Imprimir reporte en pantalla."""
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(datos['titulo'].center(80))
        self.stdout.write(f"Empresa: {datos['empresa']}")
        self.stdout.write(f"Fecha: {datos['fecha']}")
        self.stdout.write(f"{'='*80}\n")
        
        if 'filas' in datos:
            # Imprimir tabla
            for fila in datos['filas'][:20]:  # Limitar a 20 filas
                self.stdout.write(
                    f"{fila.get('codigo', ''): <12} "
                    f"{fila.get('descripcion', ''): <30} "
                    f"{str(fila.get('debe', '')): >15} "
                    f"{str(fila.get('haber', '')): >15} "
                    f"{str(fila.get('saldo', '')): >15}"
                )
