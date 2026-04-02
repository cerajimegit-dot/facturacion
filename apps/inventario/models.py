"""Almacen, Stock, MovimientoStock models."""
import uuid
from django.db import models
from apps.core.models import TenantModel, TenantManager


class Almacen(TenantModel):
    """Warehouse / storage location."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=20)
    nombre = models.CharField(max_length=255)
    direccion = models.TextField(blank=True, default='')
    activo = models.BooleanField(default=True)

    objects = TenantManager()

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Almacén'
        verbose_name_plural = 'Almacenes'
        unique_together = ('empresa', 'codigo')

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Stock(TenantModel):
    """Current stock level for a product in a specific warehouse."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.ForeignKey(
        'productos.Producto', on_delete=models.CASCADE, related_name='stocks'
    )
    almacen = models.ForeignKey(
        Almacen, on_delete=models.CASCADE, related_name='stocks'
    )
    cantidad = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    cantidad_reservada = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    ubicacion = models.CharField(max_length=100, blank=True, default='')
    stock_minimo = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    objects = TenantManager()

    class Meta:
        verbose_name = 'Stock'
        verbose_name_plural = 'Stocks'
        unique_together = ('empresa', 'producto', 'almacen')

    def __str__(self):
        return f"{self.producto.sku} @ {self.almacen.codigo}: {self.cantidad}"

    @property
    def cantidad_disponible(self):
        return self.cantidad - self.cantidad_reservada


class MovimientoStock(TenantModel):
    """Stock movement log (entries, exits, adjustments)."""
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
        ('transferencia', 'Transferencia'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.ForeignKey(
        'productos.Producto', on_delete=models.CASCADE, related_name='movimientos_stock'
    )
    almacen = models.ForeignKey(
        Almacen, on_delete=models.CASCADE, related_name='movimientos'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cantidad = models.DecimalField(max_digits=15, decimal_places=2)
    referencia = models.CharField(max_length=100, blank=True, default='')
    nota = models.TextField(blank=True, default='')
    usuario = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
    )

    objects = TenantManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Movimiento de Stock'
        verbose_name_plural = 'Movimientos de Stock'

    def __str__(self):
        return f"{self.tipo} {self.cantidad} {self.producto.sku}"
