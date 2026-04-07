"""Signals para generar asientos contables automáticamente."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from decimal import Decimal
from django.utils import timezone
from datetime import datetime

from apps.compras.models import Compra
from apps.contabilidad.models import Asiento, LineaAsiento
from apps.productos.models import Producto
from apps.compras.models import Proveedor


@receiver(post_save, sender=Compra)
def generar_asiento_compra(sender, instance, created, **kwargs):
    """
    Generar asiento contable automáticamente al recibir una compra.
    
    Debe: Cuenta contable del producto
    Haber: Cuenta contable del proveedor
    """
    if not created or instance.estado == 'pendiente':
        return
    
    try:
        empresa = instance.empresa
        
        # Validar que exista cuenta contable en proveedor
        proveedor = instance.proveedor
        if not hasattr(proveedor, 'cuenta_contable') or not proveedor.cuenta_contable:
            raise ValueError(f"Proveedor {proveedor.nombre} sin cuenta contable")
        
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
        total_haber = Decimal('0')
        
        # Crear líneas por cada detalle de compra
        for detalle in instance.detalles.all():
            producto = detalle.producto
            
            # Validar cuenta contable del producto
            if not producto or not hasattr(producto, 'cuenta_contable') or not producto.cuenta_contable:
                raise ValueError(f"Producto {detalle.descripcion} sin cuenta contable")
            
            # Convertir a PYG si es USD
            cantidad_pesos = detalle.precio_unitario * detalle.cantidad
            if instance.moneda == 'USD' and hasattr(instance, 'cotizacion_usd') and instance.cotizacion_usd:
                cantidad_pesos = cantidad_pesos * instance.cotizacion_usd
            
            # Línea de DEBE (producto)
            LineaAsiento.objects.create(
                empresa=empresa,
                asiento=asiento,
                cuenta=producto.cuenta_contable,
                debe=cantidad_pesos,
                haber=Decimal('0'),
                observacion=f"Compra {detalle.descripcion}",
                item_contable=_generar_item_contable(proveedor),
                compra_detalle=detalle,
            )
            total_debe += cantidad_pesos
        
        # Línea de HABER (proveedor)
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=proveedor.cuenta_contable,
            debe=Decimal('0'),
            haber=total_debe,
            observacion=f"Proveedor: {proveedor.nombre}",
            item_contable=_generar_item_contable(proveedor),
        )
        total_haber = total_debe
        
        # Actualizar totales del asiento
        asiento.total_debe = total_debe
        asiento.total_haber = total_haber
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
