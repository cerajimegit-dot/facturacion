"""Cotizacion, Venta, LineaVenta, CuentaPorCobrar, NotaCredito models."""
import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from apps.core.models import TenantModel, TenantManager


# Tasas de IVA legales en Paraguay (Ley 6380/19, Art. 83)
CONDICION_IVA_CHOICES = [
    ('gravada_10', 'Gravada 10%'),
    ('gravada_5', 'Gravada 5%'),
    ('exenta', 'Exenta'),
]

IVA_TASA_MAP = {
    'gravada_10': Decimal('10'),
    'gravada_5': Decimal('5'),
    'exenta': Decimal('0'),
}

TIPO_COMPROBANTE_CHOICES = [
    ('factura', 'Factura'),
    ('nota_credito', 'Nota de Crédito'),
    ('nota_debito', 'Nota de Débito'),
    ('autofactura', 'Autofactura'),
]


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
    tipo_comprobante = models.CharField(
        max_length=20, choices=TIPO_COMPROBANTE_CHOICES, default='factura',
        help_text='Tipo de comprobante fiscal'
    )
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
    
    # Observaciones de cobro y avance
    observaciones_cobro = models.TextField(blank=True, default='', help_text='Observaciones sobre pagos y avance de cobro')

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


class LineaVenta(TenantModel):
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
    condicion_iva = models.CharField(
        max_length=15, choices=CONDICION_IVA_CHOICES, default='gravada_10',
        help_text='Condición de IVA según Ley 6380/19'
    )
    impuesto_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    impuesto_monto = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    objects = TenantManager()

    class Meta:
        verbose_name = 'Línea de Venta'
        verbose_name_plural = 'Líneas de Venta'

    def save(self, *args, **kwargs):
        # Forzar tasa IVA legal desde condicion_iva
        self.impuesto_porcentaje = IVA_TASA_MAP.get(self.condicion_iva, Decimal('10'))
        self.subtotal = self.cantidad * self.precio_unitario
        descuento = self.subtotal * (Decimal(str(self.descuento_porcentaje)) / Decimal('100'))
        base_imponible = self.subtotal - descuento
        self.impuesto_monto = base_imponible * (self.impuesto_porcentaje / Decimal('100'))
        self.total = base_imponible + self.impuesto_monto
        # Inherit empresa from venta if not set
        if not self.empresa_id and self.venta_id:
            self.empresa_id = self.venta.empresa_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto.sku} x {self.cantidad}"


class LineaCotizacion(TenantModel):
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
    condicion_iva = models.CharField(
        max_length=15, choices=CONDICION_IVA_CHOICES, default='gravada_10',
        help_text='Condición de IVA según Ley 6380/19'
    )
    impuesto_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    impuesto_monto = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    objects = TenantManager()

    class Meta:
        verbose_name = 'Línea de Cotización'
        verbose_name_plural = 'Líneas de Cotización'

    def save(self, *args, **kwargs):
        self.impuesto_porcentaje = IVA_TASA_MAP.get(self.condicion_iva, Decimal('10'))
        self.subtotal = self.cantidad * self.precio_unitario
        descuento = self.subtotal * (Decimal(str(self.descuento_porcentaje)) / Decimal('100'))
        base_imponible = self.subtotal - descuento
        self.impuesto_monto = base_imponible * (self.impuesto_porcentaje / Decimal('100'))
        self.total = base_imponible + self.impuesto_monto
        if not self.empresa_id and self.cotizacion_id:
            self.empresa_id = self.cotizacion.empresa_id
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
        ('anulada', 'Anulada'),
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


class RegistroPago(TenantModel):
    """Record of partial payments for invoices."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venta = models.ForeignKey(
        Venta, on_delete=models.CASCADE, related_name='registro_pagos'
    )
    monto = models.DecimalField(max_digits=15, decimal_places=2)
    fecha_pago = models.DateTimeField(auto_now_add=True)
    metodo_pago = models.CharField(max_length=50, blank=True, default='')
    referencia = models.CharField(max_length=100, blank=True, default='')
    observaciones = models.TextField(blank=True, default='')
    
    objects = TenantManager()
    
    class Meta:
        ordering = ['-fecha_pago']
        verbose_name = 'Registro de Pago'
        verbose_name_plural = 'Registros de Pago'
    
    def __str__(self):
        return f"Pago {self.monto} - {self.venta.numero}"


class NotaCredito(TenantModel):
    """Nota de Crédito vinculada a una factura original."""
    MOTIVO_CHOICES = [
        ('devolucion', 'Devolución de mercadería'),
        ('descuento', 'Descuento posterior'),
        ('bonificacion', 'Bonificación'),
        ('error_facturacion', 'Error de facturación'),
        ('otro', 'Otro'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=30, db_index=True)
    venta_original = models.ForeignKey(
        Venta, on_delete=models.PROTECT, related_name='notas_credito',
        help_text='Factura original que se corrige'
    )
    cliente = models.ForeignKey(
        'clientes.Cliente', on_delete=models.CASCADE, related_name='notas_credito'
    )
    fecha = models.DateField()
    motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES)
    descripcion = models.TextField(blank=True, default='')
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    impuestos = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    estado = models.CharField(
        max_length=20,
        choices=[('borrador', 'Borrador'), ('confirmada', 'Confirmada'), ('anulada', 'Anulada')],
        default='borrador'
    )

    objects = TenantManager()

    class Meta:
        ordering = ['-fecha', '-numero']
        verbose_name = 'Nota de Crédito'
        verbose_name_plural = 'Notas de Crédito'
        unique_together = ('empresa', 'numero')

    def __str__(self):
        return f"NC-{self.numero} (ref: {self.venta_original.numero})"

    def recalcular_totales(self):
        lineas = self.lineas.all()
        self.subtotal = sum(l.subtotal for l in lineas)
        self.impuestos = sum(l.impuesto_monto for l in lineas)
        self.total = self.subtotal + self.impuestos
        self.save(update_fields=['subtotal', 'impuestos', 'total'])


class LineaNotaCredito(TenantModel):
    """Línea de una Nota de Crédito."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nota_credito = models.ForeignKey(NotaCredito, on_delete=models.CASCADE, related_name='lineas')
    producto = models.ForeignKey(
        'productos.Producto', on_delete=models.CASCADE, related_name='lineas_nota_credito'
    )
    descripcion = models.CharField(max_length=255, blank=True, default='')
    cantidad = models.DecimalField(max_digits=15, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)
    condicion_iva = models.CharField(
        max_length=15, choices=CONDICION_IVA_CHOICES, default='gravada_10'
    )
    impuesto_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    impuesto_monto = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    objects = TenantManager()

    class Meta:
        verbose_name = 'Línea de Nota de Crédito'
        verbose_name_plural = 'Líneas de Nota de Crédito'

    def save(self, *args, **kwargs):
        self.impuesto_porcentaje = IVA_TASA_MAP.get(self.condicion_iva, Decimal('10'))
        self.subtotal = self.cantidad * self.precio_unitario
        self.impuesto_monto = self.subtotal * (self.impuesto_porcentaje / Decimal('100'))
        self.total = self.subtotal + self.impuesto_monto
        if not self.empresa_id and self.nota_credito_id:
            self.empresa_id = self.nota_credito.empresa_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.producto.sku} x {self.cantidad} (NC)"

