"""Command para generar datos de demostración para contabilidad."""
from datetime import datetime, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.empresas.models import Empresa
from apps.compras.models import Proveedor
from apps.productos.models import Producto
from apps.contabilidad.models import PlanCuentas, CotizacionDiaria, Asiento, LineaAsiento
from apps.usuarios.models import Usuario


class Command(BaseCommand):
    help = 'Generar datos de demostración para contabilidad'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--empresa-id',
            type=str,
            help='ID de la empresa (si no se proporciona, usa la primera)'
        )
        parser.add_argument(
            '--limpiar',
            action='store_true',
            help='Limpiar datos existentes primero'
        )
    
    @transaction.atomic
    def handle(self, *args, **options):
        empresa_id = options.get('empresa_id')
        limpiar = options.get('limpiar', False)
        
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
        
        self.stdout.write(f"📌 Generando datos de demo para: {empresa.nombre}\n")
        
        # Limpiar si se pide
        if limpiar:
            self._limpiar_datos(empresa)
        
        # Obtener usuario admin
        usuario = Usuario.objects.filter(is_superuser=True).first()
        if not usuario:
            raise CommandError('No hay usuarios administradores')
        
        # 1. Crear plan de cuentas de demo
        self.stdout.write("1️⃣  Creando plan de cuentas...")
        plan = self._crear_plan_cuentas(empresa)
        
        # 2. Crear proveedores de demo
        self.stdout.write("2️⃣  Creando proveedores...")
        proveedores = self._crear_proveedores(empresa, plan)
        
        # 3. Crear productos de demo
        self.stdout.write("3️⃣  Creando productos...")
        productos = self._crear_productos(empresa, plan)
        
        # 4. Crear cotizaciones de demo
        self.stdout.write("4️⃣  Creando cotizaciones...")
        self._crear_cotizaciones(empresa, usuario)
        
        # 5. Crear asientos de demo
        self.stdout.write("5️⃣  Creando asientos...")
        self._crear_asientos(empresa, usuario)
        
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("✅ Datos de demostración creados correctamente"))
    
    def _limpiar_datos(self, empresa):
        """Limpiar datos existentes."""
        count = 0
        count += Asiento.objects.filter(empresa=empresa).delete()[0]
        count += LineaAsiento.objects.filter(asiento__empresa=empresa).delete()[0]
        count += CotizacionDiaria.objects.filter(empresa=empresa).delete()[0]
        self.stdout.write(f"🗑️  Eliminados {count} registros existentes\n")
    
    def _crear_plan_cuentas(self, empresa):
        """Crear plan de cuentas de demostración."""
        cuentas = [
            # ACTIVOS (deudora)
            ('1000', 'ACTIVOS', 'deudora', 'sintetica'),
            ('1100', 'ACTIVOS CIRCULANTES', 'deudora', 'sintetica'),
            ('1110', 'Caja', 'deudora', 'analitica'),
            ('1120', 'Bancos', 'deudora', 'analitica'),
            ('1130', 'Cuentas por Cobrar', 'deudora', 'analitica'),
            ('1200', 'INVENTARIOS', 'deudora', 'sintetica'),
            ('1210', 'Productos en Stock', 'deudora', 'analitica'),
            ('1300', 'ACTIVOS NO CIRCULANTES', 'deudora', 'sintetica'),
            ('1310', 'Propiedad, Planta y Equipo', 'deudora', 'analitica'),
            
            # PASIVOS (acreedora)
            ('2000', 'PASIVOS', 'acreedora', 'sintetica'),
            ('2100', 'PASIVOS CIRCULANTES', 'acreedora', 'sintetica'),
            ('2110', 'Cuentas por Pagar', 'acreedora', 'analitica'),
            ('2120', 'Impuestos por Pagar', 'acreedora', 'analitica'),
            ('2200', 'PASIVOS NO CIRCULANTES', 'acreedora', 'sintetica'),
            ('2210', 'Deuda a Largo Plazo', 'acreedora', 'analitica'),
            
            # PATRIMONIO (acreedora)
            ('3000', 'PATRIMONIO', 'acreedora', 'sintetica'),
            ('3100', 'Capital Social', 'acreedora', 'analitica'),
            ('3200', 'Resultados Acumulados', 'acreedora', 'analitica'),
            
            # INGRESOS (acreedora)
            ('4000', 'INGRESOS', 'acreedora', 'sintetica'),
            ('4100', 'Ventas', 'acreedora', 'analitica'),
            ('4200', 'Ingresos Diversos', 'acreedora', 'analitica'),
            
            # GASTOS (deudora)
            ('5000', 'GASTOS', 'deudora', 'sintetica'),
            ('5100', 'Costo de Ventas', 'deudora', 'analitica'),
            ('5200', 'Gastos Administrativos', 'deudora', 'analitica'),
            ('5300', 'Gastos de Venta', 'deudora', 'analitica'),
        ]
        
        for codigo, desc, condicion, clase in cuentas:
            cuenta, creada = PlanCuentas.objects.get_or_create(
                empresa=empresa,
                codigo_cuenta=codigo,
                defaults={
                    'descripcion': desc,
                    'condicion': condicion,
                    'clase': clase,
                    'acepta_item': True,
                    'acepta_centro_costo': True,
                    'acepta_nivel': False,
                }
            )
            if creada:
                self.stdout.write(f"  ✓ {codigo} - {desc}")
        
        self.stdout.write(f"  ✅ Plan de cuentas creado\n")
        
        return dict(
            (codigo, PlanCuentas.objects.get(empresa=empresa, codigo_cuenta=codigo))
            for codigo, _, _, _ in cuentas
        )
    
    def _crear_proveedores(self, empresa, plan):
        """Crear proveedores de demostración."""
        proveedores_data = [
            ('PROV001', '500000', 'Proveedor A S.A.', 'contacto@proveedora.py'),
            ('PROV002', '600000', 'Proveedor B Ltda.', 'info@proveedorb.py'),
            ('PROV003', '700000', 'Distribuidora C', 'ventas@distribuidorac.py'),
        ]
        
        proveedores = []
        for codigo, ruc, nombre, email in proveedores_data:
            proveedor, creada = Proveedor.objects.get_or_create(
                empresa=empresa,
                ruc_numero=ruc,
                defaults={
                    'nombre': nombre,
                    'email': email,
                    'cuenta_contable': plan.get('2110'),  # Cuentas por Pagar
                    'emite_electronica': True,
                }
            )
            if creada:
                self.stdout.write(f"  ✓ {nombre} (RUC: {ruc})")
            proveedores.append(proveedor)
        
        self.stdout.write(f"  ✅ {len(proveedores)} proveedores creados\n")
        return proveedores
    
    def _crear_productos(self, empresa, plan):
        """Crear productos de demostración."""
        productos_data = [
            ('PROD001', 'Producto A', Decimal('100.00')),
            ('PROD002', 'Producto B', Decimal('250.50')),
            ('PROD003', 'Producto C', Decimal('75.25')),
        ]
        
        productos = []
        for codigo, desc, precio in productos_data:
            producto, creada = Producto.objects.get_or_create(
                empresa=empresa,
                codigo=codigo,
                defaults={
                    'descripcion': desc,
                    'precio_unitario': precio,
                    'cuenta_contable': plan.get('1210'),  # Inventario
                }
            )
            if creada:
                self.stdout.write(f"  ✓ {desc}")
            productos.append(producto)
        
        self.stdout.write(f"  ✅ {len(productos)} productos creados\n")
        return productos
    
    def _crear_cotizaciones(self, empresa, usuario):
        """Crear cotizaciones de demostración."""
        hoy = datetime.now().date()
        pares = [
            ('USD', 'PYG', Decimal('6600')),
            ('USD', 'ARS', Decimal('830')),
            ('EUR', 'PYG', Decimal('7200')),
        ]
        
        count = 0
        for dias_atras in range(7):
            fecha = hoy - timedelta(days=dias_atras)
            for moneda_origen, moneda_destino, tasa in pares:
                cotizacion, creada = CotizacionDiaria.objects.get_or_create(
                    empresa=empresa,
                    fecha=fecha,
                    moneda_origen=moneda_origen,
                    moneda_destino=moneda_destino,
                    defaults={
                        'tasa': tasa,
                        'fuente': 'Demo',
                        'usuario_carga': usuario,
                    }
                )
                if creada:
                    count += 1
        
        self.stdout.write(f"  ✅ {count} cotizaciones creadas\n")
    
    def _crear_asientos(self, empresa, usuario):
        """Crear asientos de demostración."""
        # Obtener las cuentas
        cuentas = {
            codigo: PlanCuentas.objects.get(empresa=empresa, codigo_cuenta=codigo)
            for codigo in ['1210', '2110', '5100']
        }
        
        # Crear asientos de compra
        count = 0
        for i in range(3):
            asiento = Asiento.objects.create(
                empresa=empresa,
                tipo_asiento='compra',
                fecha_asiento=datetime.now().date() - timedelta(days=i),
                estado='registrado',
                usuario_creador=usuario,
                observacion=f'Asiento de demo {i+1}',
            )
            
            # Línea DEBE (Inventario)
            LineaAsiento.objects.create(
                asiento=asiento,
                cuenta=cuentas['1210'],
                debe=Decimal('1000.00'),
                haber=Decimal('0'),
                observacion='Compra de inventario',
                item_contable='P500000',
            )
            
            # Línea HABER (Cuentas por Pagar)
            LineaAsiento.objects.create(
                asiento=asiento,
                cuenta=cuentas['2110'],
                debe=Decimal('0'),
                haber=Decimal('1000.00'),
                observacion='A pagar a proveedor',
            )
            
            count += 1
            self.stdout.write(f"  ✓ Asiento #{asiento.numero_asiento}")
        
        self.stdout.write(f"  ✅ {count} asientos creados\n")
