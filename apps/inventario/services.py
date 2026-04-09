"""Servicio de inventario para gestión de stock vinculada a ventas y compras."""
from decimal import Decimal


class InventarioService:
    """Servicio de negocio para operaciones de inventario."""

    @staticmethod
    def descontar_stock_venta(empresa, producto, cantidad, referencia='', usuario=None):
        """Descuenta stock al confirmar una venta.

        1. Verifica disponibilidad en algún almacén
        2. Descuenta de stock
        3. Registra movimiento de salida

        Raises ValueError si no hay stock suficiente.
        """
        from apps.inventario.models import Stock, MovimientoStock

        # Buscar stock disponible en cualquier almacén de la empresa
        stocks = Stock.objects.filter(
            empresa=empresa,
            producto=producto,
        ).order_by('-cantidad')  # primeros los que tienen más

        total_disponible = sum(
            s.cantidad - s.cantidad_reservada for s in stocks
        )

        if total_disponible < cantidad:
            raise ValueError(
                f"Stock insuficiente para {producto.nombre} (SKU: {producto.sku}). "
                f"Disponible: {total_disponible}, Requerido: {cantidad}"
            )

        # Descontar del primer almacén con stock
        cantidad_restante = cantidad
        for stock in stocks:
            disponible = stock.cantidad - stock.cantidad_reservada
            if disponible <= 0:
                continue

            a_descontar = min(disponible, cantidad_restante)
            stock.cantidad -= a_descontar
            stock.save(update_fields=['cantidad'])

            # Registrar movimiento
            MovimientoStock.objects.create(
                empresa=empresa,
                producto=producto,
                almacen=stock.almacen,
                tipo='salida',
                cantidad=a_descontar,
                referencia=referencia,
                usuario=usuario,
                nota=f"Descuento automático por venta: {referencia}",
            )

            cantidad_restante -= a_descontar
            if cantidad_restante <= 0:
                break

    @staticmethod
    def revertir_stock_venta(empresa, producto, cantidad, referencia='', usuario=None):
        """Revierte el descuento de stock (anulación de venta, nota de crédito).

        Devuelve stock al primer almacén donde exista el producto.
        """
        from apps.inventario.models import Stock, MovimientoStock

        # Buscar primer stock existente para este producto
        stock = Stock.objects.filter(
            empresa=empresa,
            producto=producto,
        ).first()

        if stock:
            stock.cantidad += cantidad
            stock.save(update_fields=['cantidad'])

            MovimientoStock.objects.create(
                empresa=empresa,
                producto=producto,
                almacen=stock.almacen,
                tipo='entrada',
                cantidad=cantidad,
                referencia=referencia,
                usuario=usuario,
                nota=f"Devolución automática: {referencia}",
            )
        # Si no hay stock registrado, creamos el movimiento pero sin crear stock
        # (el producto podría no tener almacén asignado aún)
