"""Signals para generar asientos contables automáticamente."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from datetime import datetime

from apps.compras.models import Compra
from apps.contabilidad.models import Asiento, LineaAsiento, PlanCuentas, CotizacionDiaria
from apps.productos.models import Producto
from apps.compras.models import Proveedor

# Código fijo de la cuenta de IVA Crédito Fiscal
IVA_CREDITO_FISCAL_CODIGO = '1.01.03.05.03'


@receiver(post_save, sender=Compra)
def generar_asiento_compra(sender, instance, created, **kwargs):
    """
    Generar asiento contable automáticamente al recibir una compra.
    
    Por cada detalle con IVA:
      Debe: Cuenta contable del producto → subtotal (sin IVA)
      Debe: 1.01.03.05.03 IVA CRÉDITO FISCAL → monto IVA
    Haber: Cuenta contable del proveedor → total (con IVA)
    """
    # Solo generar asiento cuando la compra es recepcionada
    if instance.estado != 'recepcionada':
        return
    
    # Evitar duplicados
    if Asiento.objects.filter(compra=instance).exists():
        return
    
    try:
        empresa = instance.empresa
        
        # Validar que exista cuenta contable en proveedor
        proveedor = instance.proveedor
        if not hasattr(proveedor, 'cuenta_contable') or not proveedor.cuenta_contable:
            raise ValueError(f"Proveedor {proveedor.nombre} sin cuenta contable")
        
        # Obtener cuenta IVA Crédito Fiscal
        cuenta_iva = PlanCuentas.objects.filter(
            empresa=empresa,
            codigo_cuenta=IVA_CREDITO_FISCAL_CODIGO,
            activa=True
        ).first()
        if not cuenta_iva:
            raise ValueError(
                f"Cuenta {IVA_CREDITO_FISCAL_CODIGO} (IVA Crédito Fiscal) "
                f"no encontrada para empresa {empresa.nombre}"
            )
        
        # Crear asiento
        numero_asiento = _generar_numero_asiento(empresa)
        asiento = Asiento.objects.create(
            empresa=empresa,
            numero_asiento=numero_asiento,
            tipo_asiento='COMPRA',
            fecha=instance.fecha,
            descripcion=f"Compra a {proveedor.nombre} - Factura {instance.numero}",
            compra=instance,
            moneda=instance.moneda,
            estado='registrado',
            usuario_crea=instance.usuario_registra if hasattr(instance, 'usuario_registra') else None,
        )
        
        total_debe = Decimal('0')
        total_iva = Decimal('0')
        
        # Crear líneas por cada detalle de compra
        for detalle in instance.detalles.all():
            producto = detalle.producto
            
            # Validar cuenta contable del producto
            if not producto or not hasattr(producto, 'cuenta_contable') or not producto.cuenta_contable:
                raise ValueError(f"Producto {detalle.descripcion} sin cuenta contable")
            
            # Precio incluye IVA: total = precio * cantidad, neto = total / (1 + iva%)
            total_linea = detalle.precio_unitario * detalle.cantidad
            if detalle.impuesto_porcentaje and detalle.impuesto_porcentaje > 0:
                divisor = Decimal('1') + (detalle.impuesto_porcentaje / Decimal('100'))
                subtotal_neto = (total_linea / divisor).quantize(Decimal('0.01'))
                monto_iva = total_linea - subtotal_neto
            else:
                subtotal_neto = total_linea
                monto_iva = Decimal('0')
            
            # Convertir a PYG si es USD usando cotización diaria
            if instance.moneda == 'USD':
                cotizacion = CotizacionDiaria.objects.filter(
                    empresa=empresa,
                    fecha=instance.fecha,
                    moneda_origen='USD',
                    moneda_destino='PYG',
                ).first()
                if not cotizacion:
                    raise ValueError(
                        f"No hay cotización USD/PYG para la fecha {instance.fecha}. "
                        f"Cargue la cotización del día antes de recepcionar."
                    )
                tasa = cotizacion.tasa
                subtotal_neto = (subtotal_neto * tasa).quantize(Decimal('0.01'))
                monto_iva = (monto_iva * tasa).quantize(Decimal('0.01'))
            
            # Línea DEBE: cuenta del producto (subtotal sin IVA)
            LineaAsiento.objects.create(
                empresa=empresa,
                asiento=asiento,
                cuenta=producto.cuenta_contable,
                debe=subtotal_neto,
                haber=Decimal('0'),
                observacion=f"Compra {detalle.descripcion}",
                item_contable=_generar_item_contable(proveedor),
                compra_detalle=detalle,
            )
            total_debe += subtotal_neto
            
            # Línea DEBE: IVA Crédito Fiscal (monto IVA)
            if monto_iva > 0:
                LineaAsiento.objects.create(
                    empresa=empresa,
                    asiento=asiento,
                    cuenta=cuenta_iva,
                    debe=monto_iva,
                    haber=Decimal('0'),
                    observacion=f"IVA {detalle.impuesto_porcentaje}% - {detalle.descripcion}",
                    item_contable=_generar_item_contable(proveedor),
                    compra_detalle=detalle,
                )
                total_iva += monto_iva
        
        total_debe_completo = total_debe + total_iva
        
        # Línea de HABER (proveedor) - total con IVA
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=proveedor.cuenta_contable,
            debe=Decimal('0'),
            haber=total_debe_completo,
            observacion=f"Proveedor: {proveedor.nombre}",
            item_contable=_generar_item_contable(proveedor),
        )
        
        # Actualizar totales del asiento
        asiento.total_debe = total_debe_completo
        asiento.total_haber = total_debe_completo
        asiento.validate_balance()
        asiento.save()
        
    except Exception as e:
        # No fallar la compra, solo loguear el error
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error generando asiento para compra {instance.id}: {str(e)}")


def _generar_numero_asiento(empresa):
    """Generar número de asiento correlativo."""
    from apps.contabilidad.models import Asiento
    ultimo = Asiento.objects.filter(empresa=empresa).order_by('-numero_asiento').first()
    
    if ultimo and ultimo.numero_asiento.isdigit():
        numero = int(ultimo.numero_asiento) + 1
    else:
        numero = int(datetime.now().strftime("%Y%m%d")) * 1000 + 1
    
    return str(numero).zfill(10)


def _generar_item_contable(proveedor):
    """Generar item contable: P + RUC."""
    return f"P{proveedor.ruc_numero}"
