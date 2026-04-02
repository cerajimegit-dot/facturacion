"""Cotizacion, Venta, LineaVenta, CuentaPorCobrar models."""
import uuid
from decimal import Decimal
from django.db import models
from apps.core.models import TenantModel, TenantManager


class Cotizacion(TenantModel):
    """Sales quotation."""
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviada', 'Enviada'),
        ('aceptada', 'Aceptada'),
        ('rechazada', 'Rechazada'),
        ('vencida', 'Vencida'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=30, db_index=True)
    cliente = models.ForeignKey(
        'clientes.Cliente', on_delete=models.CASCADE, related_name='cotizaciones'
    )
    fecha = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    moneda = models.CharField(max_length=3, default='PYG')
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notas = models.TextField(blank=True, default='')
    vendedor = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
    )

    objects = TenantManager()

    class Meta:
        ordering = ['-fecha', '-numero']
        verbose_name = 'Cotización'
        verbose_name_plural = 'Cotizaciones'
        unique_together = ('empresa', 'numero')

    def __str__(self):
        return f"COT-{self.numero}"


class Venta(TenantModel):
    """Sales invoice / factura."""
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('confirmada', 'Confirmada'),
        ('facturada', 'Facturada'),
        ('parcial', 'Pago Parcial'),
        ('pagada', 'Pagada'),
        ('anulada', 'Anulada'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=30, db_index=True)
    cliente = models.ForeignKey(
        'clientes.Cliente', on_delete=models.CASCADE, related_name='ventas'
    )
    cotizacion = models.ForeignKey(
        Cotizacion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ventas',
    )
    fecha = models.DateField()
    fecha_vencimiento = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    moneda = models.CharField(max_length=3, default='PYG')
    tipo_cambio = models.DecimalField(max_digits=12, decimal_places=4, default=1)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_pagado = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    saldo_pendiente = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    metodo_pago = models.CharField(max_length=50, blank=True, default='')
    notas = models.TextField(blank=True, default='')
    vendedor = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
    )
    # SIFEN fields (future integration)
    timbrado = models.CharField(max_length=30, blank=True, default='')
    cdc = models.CharField(max_length=50, blank=True, default='')

    objects = TenantManager()

    class Meta:
        ordering = ['-fecha', '-numero']
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        unique_together = ('empresa', 'numero')

    def __str__(self):
        return f"VTA-{self.numero}"

    def recalcular_totales(self):
        """Recalculate totals from line items."""
        lineas = self.lineas.all()
        self.subtotal = sum(l.subtotal for l in lineas)
        self.impuestos = sum(l.impuesto_monto for l in lineas)
        self.total = self.subtotal + self.impuestos - self.descuento
        self.saldo_pendiente = self.total - self.total_pagado
        self.save(update_fields=['subtotal', 'impuestos', 'total', 'saldo_pendiente'])


class LineaVenta(models.Model):
    """Line item in a sale."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='lineas')
    producto = models.ForeignKey(
        'productos.Producto', on_delete=models.CASCADE, related_name='lineas_venta'
    )
    descripcion = models.CharField(max_length=255, blank=True, default='')
    cantidad = models.DecimalField(max_digits=15, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    impuesto_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    impuesto_monto = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Línea de Venta'
        verbose_name_plural = 'Líneas de Venta'

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        descuento = self.subtotal * (Decimal(str(self.descuento_porcentaje)) / Decimal('100'))
        base_imponible = self.subtotal - descuento
        self.impuesto_monto = base_imponible * (Decimal(str(self.impuesto_porcentaje)) / Decimal('100'))
        self.total = base_imponible + self.impuesto_monto
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto.sku} x {self.cantidad}"


class LineaCotizacion(models.Model):
    """Line item in a quotation."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name='lineas')
    producto = models.ForeignKey(
        'productos.Producto', on_delete=models.CASCADE, related_name='lineas_cotizacion'
    )
    descripcion = models.CharField(max_length=255, blank=True, default='')
    cantidad = models.DecimalField(max_digits=15, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    descuento_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    impuesto_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    impuesto_monto = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Línea de Cotización'
        verbose_name_plural = 'Líneas de Cotización'

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        descuento = self.subtotal * (Decimal(str(self.descuento_porcentaje)) / Decimal('100'))
        base_imponible = self.subtotal - descuento
        self.impuesto_monto = base_imponible * (Decimal(str(self.impuesto_porcentaje)) / Decimal('100'))
        self.total = base_imponible + self.impuesto_monto
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto.sku} x {self.cantidad}"


class CuentaPorCobrar(TenantModel):
    """Accounts receivable tracking."""
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('parcial', 'Pago Parcial'),
        ('pagada', 'Pagada'),
        ('vencida', 'Vencida'),
        ('incobrable', 'Incobrable'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, related_name='cuentas_por_cobrar'
    )
    cliente = models.ForeignKey(
        'clientes.Cliente', on_delete=models.CASCADE, related_name='cuentas_por_cobrar'
    )
    monto_original = models.DecimalField(max_digits=15, decimal_places=2)
    monto_pagado = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    saldo = models.DecimalField(max_digits=15, decimal_places=2)
    moneda = models.CharField(max_length=3, default='PYG')
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    notas = models.TextField(blank=True, default='')

    objects = TenantManager()

    class Meta:
        ordering = ['fecha_vencimiento']
        verbose_name = 'Cuenta por Cobrar'
        verbose_name_plural = 'Cuentas por Cobrar'

    def __str__(self):
        return f"CxC {self.venta.numero} - {self.cliente.nombre}: {self.saldo}"
