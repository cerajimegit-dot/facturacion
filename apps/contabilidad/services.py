"""Servicio de contabilización automática.

Genera asientos contables automáticamente al confirmar:
- Ventas (Débito CxC / Crédito Ingresos + IVA Débito Fiscal)
- Pagos (Débito Caja / Crédito CxC)
- Compras (Débito Mercadería + IVA Crédito Fiscal / Crédito CxP)
- Notas de Crédito (reverso del asiento de venta)
"""
from decimal import Decimal
from django.utils import timezone


# Cuentas contables estándar (códigos por defecto del plan de cuentas)
# Estos códigos se buscan dinámicamente en el plan de cuentas de la empresa
CUENTAS_DEFAULT = {
    'caja': '1110',                  # Caja
    'banco': '1120',                 # Bancos
    'cuentas_por_cobrar': '1130',    # Cuentas por Cobrar
    'mercaderias': '1410',           # Mercaderías
    'iva_credito_fiscal': '1510',    # IVA Crédito Fiscal
    'cuentas_por_pagar': '2110',     # Cuentas por Pagar
    'iva_debito_fiscal': '2120',     # IVA Débito Fiscal
    'ingresos_ventas': '4110',       # Ingresos por Ventas
    'costo_ventas': '5110',          # Costo de Ventas
    'devoluciones_ventas': '4120',   # Devoluciones sobre Ventas
    'gastos_operativos': '5200',     # Gastos Operativos (para gastos aprobados)
}


class ContabilidadService:
    """Servicio para generación automática de asientos contables."""

    @staticmethod
    def _get_cuenta(empresa, codigo_default):
        """Busca una cuenta contable en el plan de cuentas de la empresa.
        Busca primero por código exacto, luego por código que empiece igual.
        """
        from apps.contabilidad.models import PlanCuentas
        # Búsqueda exacta
        cuenta = PlanCuentas.objects.filter(
            empresa=empresa,
            codigo_cuenta=codigo_default,
            activa=True,
            clase='analitica',
        ).first()
        if cuenta:
            return cuenta
        # Búsqueda por prefijo (ej: buscar 1110 encuentra 11100)
        cuenta = PlanCuentas.objects.filter(
            empresa=empresa,
            codigo_cuenta__startswith=codigo_default,
            activa=True,
            clase='analitica',
        ).first()
        return cuenta

    @staticmethod
    def _get_siguiente_numero(empresa, tipo_asiento):
        """Genera el siguiente número de asiento para la empresa."""
        from apps.contabilidad.models import Asiento
        prefijos = {
            'VENTA': 'AV',
            'PAGO': 'AP',
            'COMPRA': 'AC',
            'NOTA_CREDITO': 'ANC',
            'REVERSION': 'AR',
            'GASTO': 'AG',
        }
        prefijo = prefijos.get(tipo_asiento, 'A')
        ultimo = Asiento.objects.filter(
            empresa=empresa,
            tipo_asiento=tipo_asiento,
        ).count()
        return f"{prefijo}-{(ultimo + 1):06d}"

    @staticmethod
    def generar_asiento_venta(venta, usuario=None):
        """Genera asiento contable al confirmar una venta.

        Asiento:
          Débito: Cuentas por Cobrar (total)
          Crédito: Ingresos por Ventas (subtotal - descuento)
          Crédito: IVA Débito Fiscal (impuestos)
        """
        from apps.contabilidad.models import Asiento, LineaAsiento

        empresa = venta.empresa

        # Buscar cuentas contables
        cuenta_cxc = ContabilidadService._get_cuenta(empresa, CUENTAS_DEFAULT['cuentas_por_cobrar'])
        cuenta_ingresos = ContabilidadService._get_cuenta(empresa, CUENTAS_DEFAULT['ingresos_ventas'])
        cuenta_iva_df = ContabilidadService._get_cuenta(empresa, CUENTAS_DEFAULT['iva_debito_fiscal'])

        # Si no hay plan de cuentas configurado, omitir asiento silenciosamente
        if not all([cuenta_cxc, cuenta_ingresos]):
            return None

        base_gravada = venta.total - venta.impuestos

        numero = ContabilidadService._get_siguiente_numero(empresa, 'VENTA')

        asiento = Asiento.objects.create(
            empresa=empresa,
            numero_asiento=numero,
            tipo_asiento='VENTA',
            fecha=venta.fecha,
            descripcion=f"Venta {venta.numero} - Cliente: {venta.cliente.nombre}",
            venta=venta,
            moneda=venta.moneda,
            total_debe=venta.total,
            total_haber=venta.total,
            estado='registrado',
            usuario_crea=usuario,
            usuario_registra=usuario,
            fecha_registro=timezone.now(),
        )

        # Débito: Cuentas por Cobrar
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=cuenta_cxc,
            debe=venta.total,
            haber=Decimal('0'),
            observacion=f"CxC Venta {venta.numero}",
        )

        # Crédito: Ingresos por Ventas
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=cuenta_ingresos,
            debe=Decimal('0'),
            haber=base_gravada,
            observacion=f"Ingreso Venta {venta.numero}",
        )

        # Crédito: IVA Débito Fiscal (si hay impuestos y cuenta existe)
        if venta.impuestos > 0 and cuenta_iva_df:
            LineaAsiento.objects.create(
                empresa=empresa,
                asiento=asiento,
                cuenta=cuenta_iva_df,
                debe=Decimal('0'),
                haber=venta.impuestos,
                observacion=f"IVA DF Venta {venta.numero}",
            )

        return asiento

    @staticmethod
    def generar_asiento_pago(pago, usuario=None):
        """Genera asiento contable al confirmar un pago.

        Asiento:
          Débito: Caja/Banco (monto del pago)
          Crédito: Cuentas por Cobrar (monto del pago)
        """
        from apps.contabilidad.models import Asiento, LineaAsiento

        empresa = pago.empresa

        # Determinar cuenta de destino según método de pago
        metodo_cuenta = {
            'efectivo': CUENTAS_DEFAULT['caja'],
            'transferencia': CUENTAS_DEFAULT['banco'],
            'tarjeta': CUENTAS_DEFAULT['banco'],
            'cheque': CUENTAS_DEFAULT['banco'],
        }
        codigo_destino = metodo_cuenta.get(pago.metodo, CUENTAS_DEFAULT['caja'])

        cuenta_destino = ContabilidadService._get_cuenta(empresa, codigo_destino)
        cuenta_cxc = ContabilidadService._get_cuenta(empresa, CUENTAS_DEFAULT['cuentas_por_cobrar'])

        if not all([cuenta_destino, cuenta_cxc]):
            return None

        numero = ContabilidadService._get_siguiente_numero(empresa, 'PAGO')

        asiento = Asiento.objects.create(
            empresa=empresa,
            numero_asiento=numero,
            tipo_asiento='PAGO',
            fecha=pago.fecha,
            descripcion=f"Cobro Venta {pago.venta.numero} - {pago.get_metodo_display()}",
            moneda=pago.moneda,
            total_debe=pago.monto,
            total_haber=pago.monto,
            estado='registrado',
            usuario_crea=usuario,
            usuario_registra=usuario,
            fecha_registro=timezone.now(),
        )

        # Débito: Caja/Banco
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=cuenta_destino,
            debe=pago.monto,
            haber=Decimal('0'),
            observacion=f"Cobro {pago.get_metodo_display()} Venta {pago.venta.numero}",
        )

        # Crédito: Cuentas por Cobrar
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=cuenta_cxc,
            debe=Decimal('0'),
            haber=pago.monto,
            observacion=f"Cancelación CxC Venta {pago.venta.numero}",
        )

        return asiento

    @staticmethod
    def generar_asiento_compra(compra, usuario=None):
        """Genera asiento contable al recibir una compra.

        Asiento:
          Débito: Mercaderías (subtotal)
          Débito: IVA Crédito Fiscal (impuestos)
          Crédito: Cuentas por Pagar (total)
        """
        from apps.contabilidad.models import Asiento, LineaAsiento

        empresa = compra.empresa

        cuenta_mercaderias = ContabilidadService._get_cuenta(empresa, CUENTAS_DEFAULT['mercaderias'])
        cuenta_iva_cf = ContabilidadService._get_cuenta(empresa, CUENTAS_DEFAULT['iva_credito_fiscal'])
        cuenta_cxp = ContabilidadService._get_cuenta(empresa, CUENTAS_DEFAULT['cuentas_por_pagar'])

        if not all([cuenta_mercaderias, cuenta_cxp]):
            return None

        numero = ContabilidadService._get_siguiente_numero(empresa, 'COMPRA')

        asiento = Asiento.objects.create(
            empresa=empresa,
            numero_asiento=numero,
            tipo_asiento='COMPRA',
            fecha=compra.fecha,
            descripcion=f"Compra {compra.numero} - Proveedor: {compra.proveedor.nombre}",
            compra=compra,
            moneda=compra.moneda,
            total_debe=compra.total,
            total_haber=compra.total,
            estado='registrado',
            usuario_crea=usuario,
            usuario_registra=usuario,
            fecha_registro=timezone.now(),
        )

        # Débito: Mercaderías
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=cuenta_mercaderias,
            debe=compra.subtotal,
            haber=Decimal('0'),
            observacion=f"Compra {compra.numero} - {compra.proveedor.nombre}",
            item_contable=compra.proveedor.item_contable,
        )

        # Débito: IVA Crédito Fiscal
        if compra.impuestos_total > 0 and cuenta_iva_cf:
            LineaAsiento.objects.create(
                empresa=empresa,
                asiento=asiento,
                cuenta=cuenta_iva_cf,
                debe=compra.impuestos_total,
                haber=Decimal('0'),
                observacion=f"IVA CF Compra {compra.numero}",
            )

        # Crédito: Cuentas por Pagar
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=cuenta_cxp,
            debe=Decimal('0'),
            haber=compra.total,
            observacion=f"CxP Compra {compra.numero} - {compra.proveedor.nombre}",
            item_contable=compra.proveedor.item_contable,
        )

        return asiento

    @staticmethod
    def generar_asiento_nota_credito(nota_credito, usuario=None):
        """Genera asiento contable para nota de crédito (reverso parcial de venta).

        Asiento:
          Débito: Devoluciones sobre Ventas / Ingresos (monto NC)
          Crédito: Cuentas por Cobrar (monto NC)
        """
        from apps.contabilidad.models import Asiento, LineaAsiento

        empresa = nota_credito.empresa
        base_gravada = nota_credito.total - nota_credito.impuestos

        cuenta_devol = ContabilidadService._get_cuenta(empresa, CUENTAS_DEFAULT['devoluciones_ventas'])
        if not cuenta_devol:
            cuenta_devol = ContabilidadService._get_cuenta(empresa, CUENTAS_DEFAULT['ingresos_ventas'])
        cuenta_cxc = ContabilidadService._get_cuenta(empresa, CUENTAS_DEFAULT['cuentas_por_cobrar'])
        cuenta_iva_df = ContabilidadService._get_cuenta(empresa, CUENTAS_DEFAULT['iva_debito_fiscal'])

        if not all([cuenta_devol, cuenta_cxc]):
            return None

        numero = ContabilidadService._get_siguiente_numero(empresa, 'NOTA_CREDITO')

        asiento = Asiento.objects.create(
            empresa=empresa,
            numero_asiento=numero,
            tipo_asiento='NOTA_CREDITO',
            fecha=nota_credito.fecha,
            descripcion=f"NC {nota_credito.numero} - ref Venta {nota_credito.venta_original.numero}",
            moneda=nota_credito.venta_original.moneda,
            total_debe=nota_credito.total,
            total_haber=nota_credito.total,
            estado='registrado',
            usuario_crea=usuario,
            usuario_registra=usuario,
            fecha_registro=timezone.now(),
        )

        # Débito: Devoluciones / Ingresos
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=cuenta_devol,
            debe=base_gravada,
            haber=Decimal('0'),
            observacion=f"NC {nota_credito.numero}",
        )

        # Débito: IVA Débito Fiscal (reversión)
        if nota_credito.impuestos > 0 and cuenta_iva_df:
            LineaAsiento.objects.create(
                empresa=empresa,
                asiento=asiento,
                cuenta=cuenta_iva_df,
                debe=nota_credito.impuestos,
                haber=Decimal('0'),
                observacion=f"IVA DF NC {nota_credito.numero}",
            )

        # Crédito: Cuentas por Cobrar
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=cuenta_cxc,
            debe=Decimal('0'),
            haber=nota_credito.total,
            observacion=f"Ajuste CxC NC {nota_credito.numero}",
        )

        return asiento

    @staticmethod
    def reversar_asiento(asiento, usuario=None):
        """Crea un asiento de reversión (invierte debe/haber)."""
        from apps.contabilidad.models import Asiento, LineaAsiento

        numero = ContabilidadService._get_siguiente_numero(asiento.empresa, 'REVERSION')

        reverso = Asiento.objects.create(
            empresa=asiento.empresa,
            numero_asiento=numero,
            tipo_asiento='REVERSION',
            fecha=timezone.now().date(),
            descripcion=f"Reversión de {asiento.numero_asiento}: {asiento.descripcion}",
            moneda=asiento.moneda,
            total_debe=asiento.total_haber,
            total_haber=asiento.total_debe,
            estado='registrado',
            usuario_crea=usuario,
            usuario_registra=usuario,
            fecha_registro=timezone.now(),
        )

        for linea in asiento.lineas.all():
            LineaAsiento.objects.create(
                empresa=asiento.empresa,
                asiento=reverso,
                cuenta=linea.cuenta,
                debe=linea.haber,
                haber=linea.debe,
                observacion=f"REV: {linea.observacion}",
                item_contable=linea.item_contable,
                centro_costo=linea.centro_costo,
            )

        asiento.estado = 'reversado'
        asiento.save(update_fields=['estado'])

        return reverso

    @staticmethod
    def generar_asiento_gasto(gasto, usuario=None):
        """Genera asiento contable al aprobar un gasto.

        Asiento:
          Débito: Gastos Operativos (5200) o cuenta de la categoría
          Crédito: Caja (1110) — pago directo
        """
        from apps.contabilidad.models import Asiento, LineaAsiento

        empresa = gasto.empresa

        # Cuenta de gasto (buscar en categoría si tiene cuenta asociada, sino default)
        cuenta_gasto = ContabilidadService._get_cuenta(
            empresa, CUENTAS_DEFAULT['gastos_operativos']
        )
        cuenta_caja = ContabilidadService._get_cuenta(
            empresa, CUENTAS_DEFAULT['caja']
        )

        if not cuenta_gasto or not cuenta_caja:
            return None

        numero = ContabilidadService._get_siguiente_numero(empresa, 'GASTO')

        categoria_nombre = gasto.categoria.nombre if gasto.categoria else 'Sin categoría'

        asiento = Asiento.objects.create(
            empresa=empresa,
            numero_asiento=numero,
            tipo_asiento='GASTO',
            fecha=gasto.fecha,
            descripcion=f"Gasto aprobado: {gasto.descripcion} — Cat: {categoria_nombre}",
            gasto=gasto,
            moneda=gasto.moneda,
            total_debe=gasto.monto,
            total_haber=gasto.monto,
            estado='registrado',
            usuario_crea=usuario,
            usuario_registra=usuario,
            fecha_registro=timezone.now(),
        )

        # Débito: Gastos Operativos
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=cuenta_gasto,
            debe=gasto.monto,
            haber=Decimal('0'),
            observacion=f"Gasto {gasto.descripcion} ({categoria_nombre})",
        )

        # Crédito: Caja
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=cuenta_caja,
            debe=Decimal('0'),
            haber=gasto.monto,
            observacion=f"Pago gasto: {gasto.comprobante or gasto.descripcion}",
        )

        return asiento
