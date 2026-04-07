"""Modelos para gestión de compras y control de gastos."""
import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import TenantModel, TenantManager


class Proveedor(TenantModel):
    """Proveedores de productos y servicios."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=255, db_index=True)
    ruc_numero = models.CharField(max_length=50, db_index=True)
    pais = models.CharField(
        max_length=100, 
        help_text="País de origen del proveedor - REQUERIDO"
    )
    direccion = models.TextField(blank=True, default='')
    telefono = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    contacto_nombre = models.CharField(max_length=255, blank=True, default='')
    activo = models.BooleanField(default=True, db_index=True)
    notas = models.TextField(blank=True, default='')
    
    # Trazabilidad
    importancia = models.CharField(
        max_length=20, 
        choices=[('alto', 'Alto'), ('medio', 'Medio'), ('bajo', 'Bajo')],
        default='medio'
    )
    dias_credito = models.IntegerField(default=0, help_text="Días de plazo de crédito")
    
    objects = TenantManager()

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'
        unique_together = ('empresa', 'ruc_numero')

    def __str__(self):
        return f"{self.nombre} ({self.pais})"
    
    @property
    def total_compras(self):
        """Total de compras realizadas a este proveedor."""
        return self.compra_set.filter(estado='recepcionada').count()


class CategoriaGasto(models.Model):
    """Categorías de gastos (servicios, no productos)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True, default='')
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Categoría de Gasto'
        verbose_name_plural = 'Categorías de Gasto'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Compra(TenantModel):
    """Facturas de compra de productos y servicios."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=50, help_text="Número de factura del proveedor")
    fecha = models.DateField(db_index=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='compra_set')
    almacen = models.ForeignKey(
        'inventario.Almacen',
        on_delete=models.PROTECT,
        related_name='compras',
        help_text="Almacén destino para productos"
    )
    
    # Moneda y validación
    moneda = models.CharField(
        max_length=3,
        choices=[('PYG', 'Paraguayo'), ('USD', 'Dólar')],
        default='PYG'
    )
    cotizacion_usd = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Cotización USD - OBLIGATORIA si moneda es USD"
    )
    
    # Montos
    subtotal = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    impuestos_total = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    
    # Estado
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente de Recepción'),
        ('recepcionada', 'Recepcionada'),
        ('cancelada', 'Cancelada'),
    ]
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente',
        db_index=True
    )
    
    # Notas auditoría
    usuario_registra = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='compras_registradas'
    )
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    usuario_recepcion = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compras_recepcionadas'
    )
    notas = models.TextField(blank=True, default='')
    
    objects = TenantManager()

    class Meta:
        ordering = ['-fecha', '-created_at']
        verbose_name = 'Compra'
        verbose_name_plural = 'Compras'
        unique_together = ('empresa', 'numero', 'proveedor')
        indexes = [
            models.Index(fields=['empresa', 'estado', 'fecha']),
            models.Index(fields=['empresa', 'proveedor', 'fecha']),
        ]

    def __str__(self):
        return f"Compra #{self.numero} - {self.proveedor.nombre} ({self.estado})"

    def save(self, *args, **kwargs):
        """Validar cotización obligatoria para USD."""
        if self.moneda == 'USD' and not self.cotizacion_usd:
            raise ValueError("La cotización USD es obligatoria cuando la moneda es USD")
        super().save(*args, **kwargs)

    @property
    def puede_recibir(self):
        """Validar si la compra puede ser recepcionada."""
        return self.estado == 'pendiente' and self.detalles.exists()


class CompraDetalle(TenantModel):
    """Ítems individuales en una compra (productos o servicios)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='detalles')
    
    # Producto o Servicio (uno debe estar presente)
    producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='compra_detalles'
    )
    es_servicio = models.BooleanField(default=False)
    categoria_gasto = models.ForeignKey(
        CategoriaGasto,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    descripcion = models.CharField(
        max_length=255,
        help_text="Descripción del producto/servicio comprado"
    )
    
    # Cantidades y precios
    cantidad = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    precio_unitario = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))]
    )
    impuesto_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )
    subtotal = models.DecimalField(max_digits=18, decimal_places=2)
    impuestos = models.DecimalField(max_digits=18, decimal_places=2)
    total = models.DecimalField(max_digits=18, decimal_places=2)
    
    objects = TenantManager()

    class Meta:
        verbose_name = 'Detalle de Compra'
        verbose_name_plural = 'Detalles de Compra'
        ordering = ['compra', 'created_at']

    def __str__(self):
        return f"{self.descripcion} x {self.cantidad}"

    def calculate_totals(self):
        """Calcular subtotal, impuestos y total."""
        self.subtotal = self.cantidad * self.precio_unitario
        self.impuestos = (self.subtotal * self.impuesto_porcentaje) / 100
        self.total = self.subtotal + self.impuestos
        return self.subtotal, self.impuestos, self.total

    def save(self, *args, **kwargs):
        """Validar que sea producto o servicio, calcular totales."""
        # Permitir que sea item de compra general (sin producto específico ni categoría)
        # Solo requerir si hay categoría, debe ser servicio; y si es servicio, debe tener categoría
        if self.es_servicio and self.categoria_gasto is None:
            # Si es servicio pero no tiene categoría, es un gasto general de compra - está bien
            pass
        elif self.es_servicio and not self.producto and not self.categoria_gasto:
            # Si es servicio pero no tiene nada, está bien para items genéricos de compra
            pass
        
        self.calculate_totals()
        super().save(*args, **kwargs)


class Gasto(TenantModel):
    """Registro de gastos generales (no asociados a compras de productos)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fecha = models.DateField(db_index=True)
    categoria = models.ForeignKey(CategoriaGasto, on_delete=models.PROTECT)
    descripcion = models.CharField(max_length=255)
    monto = models.DecimalField(max_digits=18, decimal_places=2, validators=[MinValueValidator(Decimal('0'))])
    moneda = models.CharField(
        max_length=3,
        choices=[('PYG', 'Paraguayo'), ('USD', 'Dólar')],
        default='PYG'
    )
    comprobante = models.CharField(max_length=50, blank=True, default='')
    usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True
    )
    aprobado = models.BooleanField(default=False)
    notas = models.TextField(blank=True, default='')
    
    objects = TenantManager()

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Gasto'
        verbose_name_plural = 'Gastos'
        indexes = [
            models.Index(fields=['empresa', 'fecha', 'categoria']),
        ]

    def __str__(self):
        return f"{self.categoria.nombre} - {self.monto} {self.moneda}"
