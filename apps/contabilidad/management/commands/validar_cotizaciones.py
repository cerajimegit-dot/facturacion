"""Command para validar y generar cotizaciones faltantes."""
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.empresas.models import Empresa
from apps.contabilidad.models import CotizacionDiaria
from apps.usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Validar y generar cotizaciones diarias faltantes'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=str,
            help='ID de la empresa (si no se proporciona, todas)'
        )
        parser.add_argument(
            '--dias',
            type=int,
            default=7,
            help='Número de días hacia atrás a validar (default: 7)'
        )
        parser.add_argument(
            '--crear-faltantes',
            action='store_true',
            help='Crear cotizaciones faltantes con valores por defecto'
        )
    
    def handle(self, *args, **options):
        empresa_id = options.get('empresa_id')
        dias = options.get('dias', 7)
        crear_faltantes = options.get('crear_faltantes', False)
        
        # Obtener empresas
        if empresa_id:
            empresas = Empresa.objects.filter(id=empresa_id)
            if not empresas.exists():
                self.stdout.write(
                    self.style.ERROR(f'Empresa no encontrada: {empresa_id}')
                )
                return
        else:
            empresas = Empresa.objects.all()
        
        # Pares de monedas a validar
        pares = [
            ('USD', 'PYG'),
            ('USD', 'ARS'),
            ('EUR', 'PYG'),
        ]
        
        # Rango de fechas
        hoy = datetime.now().date()
        desde = hoy - timedelta(days=dias)
        
        self.stdout.write(f"📌 Validando cotizaciones desde {desde} hasta {hoy}")
        self.stdout.write(f"   Pares: {', '.join([f'{o}/{d}' for o, d in pares])}\n")
        
        usuario_admin = Usuario.objects.filter(is_superuser=True).first()
        if not usuario_admin:
            self.stdout.write(self.style.WARNING('⚠️  No hay usuarios admin para crear cotizaciones'))
            crear_faltantes = False
        
        total_faltantes = 0
        total_creadas = 0
        
        for empresa in empresas:
            self.stdout.write(f"\n🏢 {empresa.nombre}")
            faltantes_empresa = 0
            creadas_empresa = 0
            
            # Generar todas las fechas
            fecha_actual = desde
            while fecha_actual <= hoy:
                # Saltar fines de semana (opcional, comentado)
                # if fecha_actual.weekday() < 5:  # Monday=0, Friday=4
                
                for moneda_origen, moneda_destino in pares:
                    existe = CotizacionDiaria.objects.filter(
                        empresa=empresa,
                        fecha=fecha_actual,
                        moneda_origen=moneda_origen,
                        moneda_destino=moneda_destino,
                    ).exists()
                    
                    if not existe:
                        faltantes_empresa += 1
                        self.stdout.write(
                            f"  ❌ FALTANTE: {fecha_actual} - {moneda_origen}/{moneda_destino}"
                        )
                        
                        if crear_faltantes:
                            # Crear con valor por defecto
                            tasa_default = Decimal('0')
                            if moneda_origen == 'USD' and moneda_destino == 'PYG':
                                tasa_default = Decimal('6600')  # Tasa aproximada
                            elif moneda_origen == 'USD' and moneda_destino == 'ARS':
                                tasa_default = Decimal('830')
                            elif moneda_origen == 'EUR' and moneda_destino == 'PYG':
                                tasa_default = Decimal('7200')
                            
                            if tasa_default > 0:
                                CotizacionDiaria.objects.create(
                                    empresa=empresa,
                                    fecha=fecha_actual,
                                    moneda_origen=moneda_origen,
                                    moneda_destino=moneda_destino,
                                    tasa=tasa_default,
                                    fuente='Auto (valor aproximado)',
                                    usuario_carga=usuario_admin,
                                )
                                creadas_empresa += 1
                                self.stdout.write(
                                    self.style.SUCCESS(
                                        f"    ✅ CREADA: Tasa {tasa_default}"
                                    )
                                )
                
                fecha_actual += timedelta(days=1)
            
            total_faltantes += faltantes_empresa
            total_creadas += creadas_empresa
            
            self.stdout.write(
                f"  Resumen: {faltantes_empresa} faltantes, "
                f"{creadas_empresa} creadas"
            )
        
        # Resumen general
        self.stdout.write("\n" + "="*60)
        self.stdout.write(f"📊 Resumen total:")
        self.stdout.write(f"   Cotizaciones faltantes: {total_faltantes}")
        self.stdout.write(f"   Cotizaciones creadas: {total_creadas}")
        
        if total_faltantes > total_creadas:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  Aún hay {total_faltantes - total_creadas} "
                    "cotizaciones faltantes"
                )
            )
