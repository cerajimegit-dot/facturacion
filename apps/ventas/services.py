"""Capa de servicios para lógica de negocio de ventas.

Centraliza toda la lógica que antes estaba dispersa en los ViewSets:
- Confirmación de ventas con asiento contable + stock
- Anulación con trazabilidad correcta
- Validación de límite de crédito
- Notas de Crédito
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from apps.ventas.models import (
    Venta, CuentaPorCobrar, NotaCredito, LineaNotaCredito,
)
from apps.contabilidad.services import ContabilidadService
from apps.inventario.services import InventarioService


class VentaService:
    """Servicio de negocio para operaciones de ventas."""

    @staticmethod
    def validar_limite_credito(venta):
        """Validar que el saldo pendiente del cliente no exceda su límite de crédito.

        Raises ValueError si se excede el límite.
        """
        cliente = venta.cliente
        if cliente.limite_credito <= 0:
            return  # Sin límite configurado

        # Sumar saldo pendiente actual del cliente
        saldo_actual = CuentaPorCobrar.objects.filter(
            cliente=cliente,
            empresa=venta.empresa,
            estado__in=['pendiente', 'parcial'],
        ).exclude(
            venta=venta
        ).values_list('saldo', flat=True)

        total_pendiente = sum(saldo_actual) + venta.total

        if total_pendiente > cliente.limite_credito:
            raise ValueError(
                f"Límite de crédito excedido. "
                f"Límite: {cliente.limite_credito:,.0f}, "
                f"Pendiente actual: {sum(saldo_actual):,.0f}, "
                f"Venta: {venta.total:,.0f}, "
                f"Total resultante: {total_pendiente:,.0f}"
            )

    @staticmethod
    @transaction.atomic
    def confirmar_venta(venta, usuario=None):
        """Confirma una venta con todas las reglas de negocio:
        1. Valida estado borrador
        2. Valida límite de crédito
        3. Valida y descuenta stock
        4. Crea CuentaPorCobrar
        5. Genera asiento contable automático

        Returns: Venta actualizada
        Raises: ValueError si algo falla
        """
        if venta.estado != 'borrador':
            raise ValueError('Solo se pueden confirmar ventas en borrador.')

        if not venta.lineas.exists():
            raise ValueError('La venta debe tener al menos una línea.')

        # 1. Validar límite de crédito
        VentaService.validar_limite_credito(venta)

        # 2. Validar y descontar stock
        for linea in venta.lineas.select_related('producto'):
            if linea.producto.tipo == 'producto':
                InventarioService.descontar_stock_venta(
                    empresa=venta.empresa,
                    producto=linea.producto,
                    cantidad=linea.cantidad,
                    referencia=f"Venta {venta.numero}",
                    usuario=usuario,
                )

        # 3. Actualizar estado
        venta.estado = 'confirmada'
        venta.saldo_pendiente = venta.total
        venta.save(update_fields=['estado', 'saldo_pendiente'])

        # 4. Crear CuentaPorCobrar
        CuentaPorCobrar.objects.create(
            empresa=venta.empresa,
            venta=venta,
            cliente=venta.cliente,
            monto_original=venta.total,
            saldo=venta.total,
            moneda=venta.moneda,
            fecha_emision=venta.fecha,
            fecha_vencimiento=venta.fecha_vencimiento or venta.fecha,
        )

        # 5. Generar asiento contable
        ContabilidadService.generar_asiento_venta(venta, usuario)

        return venta

    @staticmethod
    @transaction.atomic
    def anular_venta(venta, usuario=None):
        """Anula una venta con trazabilidad correcta:
        - CxC pasa a estado 'anulada' (no 'pagada')
        - Revierte stock si estaba confirmada
        - Genera asiento de reversión
        """
        if venta.estado == 'anulada':
            raise ValueError('La venta ya está anulada.')

        estado_anterior = venta.estado

        # Revertir stock si la venta estaba confirmada
        if estado_anterior in ('confirmada', 'parcial', 'facturada'):
            for linea in venta.lineas.select_related('producto'):
                if linea.producto.tipo == 'producto':
                    InventarioService.revertir_stock_venta(
                        empresa=venta.empresa,
                        producto=linea.producto,
                        cantidad=linea.cantidad,
                        referencia=f"Anulación Venta {venta.numero}",
                        usuario=usuario,
                    )

        venta.estado = 'anulada'
        venta.save(update_fields=['estado'])

        # Marcar CxC como anulada (NO como pagada)
        venta.cuentas_por_cobrar.update(estado='anulada', saldo=0)

        # Generar asiento de reversión si existe asiento original
        if hasattr(venta, 'asiento_contable'):
            ContabilidadService.reversar_asiento(venta.asiento_contable, usuario)

        return venta

    @staticmethod
    @transaction.atomic
    def confirmar_nota_credito(nota_credito, usuario=None):
        """Confirma una nota de crédito:
        1. Ajusta saldo de la venta original
        2. Ajusta CxC
        3. Genera asiento contable de NC
        4. Devuelve stock si aplica
        """
        if nota_credito.estado != 'borrador':
            raise ValueError('Solo se pueden confirmar notas de crédito en borrador.')

        venta = nota_credito.venta_original

        # Ajustar saldo de la venta
        venta.total_pagado += nota_credito.total  # NC se contabiliza como "pago"
        venta.saldo_pendiente = venta.total - venta.total_pagado
        if venta.saldo_pendiente <= 0:
            venta.estado = 'pagada'
            venta.saldo_pendiente = Decimal('0')
        elif venta.total_pagado > 0:
            venta.estado = 'parcial'
        venta.save(update_fields=['total_pagado', 'saldo_pendiente', 'estado'])

        # Ajustar CxC
        cxc = CuentaPorCobrar.objects.filter(venta=venta).first()
        if cxc:
            cxc.monto_pagado += nota_credito.total
            cxc.saldo = cxc.monto_original - cxc.monto_pagado
            if cxc.saldo <= 0:
                cxc.estado = 'pagada'
                cxc.saldo = Decimal('0')
            else:
                cxc.estado = 'parcial'
            cxc.save(update_fields=['monto_pagado', 'saldo', 'estado'])

        # Devolver stock para líneas de productos
        for linea in nota_credito.lineas.select_related('producto'):
            if linea.producto.tipo == 'producto':
                InventarioService.revertir_stock_venta(
                    empresa=nota_credito.empresa,
                    producto=linea.producto,
                    cantidad=linea.cantidad,
                    referencia=f"NC {nota_credito.numero}",
                    usuario=usuario,
                )

        # Generar asiento contable
        ContabilidadService.generar_asiento_nota_credito(nota_credito, usuario)

        nota_credito.estado = 'confirmada'
        nota_credito.save(update_fields=['estado'])

        return nota_credito


class PagoService:
    """Servicio de negocio para operaciones de pagos."""

    @staticmethod
    @transaction.atomic
    def confirmar_pago(pago, usuario=None):
        """Confirma un pago y actualiza saldos de venta y CxC.
        Genera asiento contable automático.
        """
        if pago.estado != 'pendiente':
            raise ValueError('Solo se pueden confirmar pagos pendientes.')

        pago.estado = 'confirmado'
        pago.save(update_fields=['estado'])

        venta = pago.venta
        venta.total_pagado += pago.monto
        venta.saldo_pendiente = venta.total - venta.total_pagado
        if venta.saldo_pendiente <= 0:
            venta.estado = 'pagada'
            venta.saldo_pendiente = Decimal('0')
        else:
            venta.estado = 'parcial'
        venta.save(update_fields=['total_pagado', 'saldo_pendiente', 'estado'])

        # Actualizar CxC
        cxc = CuentaPorCobrar.objects.filter(venta=venta).first()
        if cxc:
            cxc.monto_pagado += pago.monto
            cxc.saldo = cxc.monto_original - cxc.monto_pagado
            if cxc.saldo <= 0:
                cxc.estado = 'pagada'
                cxc.saldo = Decimal('0')
            else:
                cxc.estado = 'parcial'
            cxc.save(update_fields=['monto_pagado', 'saldo', 'estado'])

        # Generar asiento contable (Débito Caja / Crédito CxC)
        ContabilidadService.generar_asiento_pago(pago, usuario)

        return pago

    @staticmethod
    @transaction.atomic
    def anular_pago(pago, usuario=None):
        """Anula un pago y revierte saldos."""
        if pago.estado != 'confirmado':
            raise ValueError('Solo se pueden anular pagos confirmados.')

        pago.estado = 'anulado'
        pago.save(update_fields=['estado'])

        venta = pago.venta
        venta.total_pagado -= pago.monto
        venta.saldo_pendiente = venta.total - venta.total_pagado
        if venta.total_pagado <= 0:
            venta.estado = 'confirmada'
            venta.total_pagado = Decimal('0')
        else:
            venta.estado = 'parcial'
        venta.save(update_fields=['total_pagado', 'saldo_pendiente', 'estado'])

        # Revertir CxC
        cxc = CuentaPorCobrar.objects.filter(venta=venta).first()
        if cxc:
            cxc.monto_pagado -= pago.monto
            cxc.saldo = cxc.monto_original - cxc.monto_pagado
            cxc.estado = 'pendiente' if cxc.monto_pagado <= 0 else 'parcial'
            if cxc.monto_pagado < 0:
                cxc.monto_pagado = Decimal('0')
            cxc.save(update_fields=['monto_pagado', 'saldo', 'estado'])

        return pago
