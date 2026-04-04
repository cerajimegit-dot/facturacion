"""Presupuesto and PresupuestoDetalle models."""
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel, TenantManager
from apps.clientes.models import Cliente
from apps.productos.models import Producto


class Presupuesto(TenantModel):
    """Budget/Quotation for a client."""
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('enviado', 'Enviado'),
        ('aceptado', 'Aceptado'),
        ('rechazado', 'Rechazado'),
        ('vencido', 'Vencido'),
        ('cancelado', 'Cancelado'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=50, unique=True, db_index=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='presupuestos')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_vigencia = models.DateField(null=True, blank=True)  # Expiration date
    fecha_envio = models.DateTimeField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    
    # Monetary details
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_impuesto = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    moneda = models.CharField(max_length=3, default='PYG')
    
    # Contact info for sending
    email_cliente = models.EmailField(blank=True, default='')
    telefono_cliente = models.CharField(max_length=50, blank=True, default='')
    
    # Additional info
    descripcion = models.TextField(blank=True, default='')
    notas = models.TextField(blank=True, default='')
    condiciones_pago = models.TextField(blank=True, default='')
    
    # Audit
    creado_por = models.ForeignKey('usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)
    
    objects = TenantManager()
    
    class Meta:
        ordering = ['-fecha_creacion']
        verbose_name = 'Presupuesto'
        verbose_name_plural = 'Presupuestos'
        indexes = [
            models.Index(fields=['empresa', 'estado']),
            models.Index(fields=['empresa', 'cliente']),
            models.Index(fields=['empresa', 'fecha_creacion']),
        ]
    
    def __str__(self):
        return f"{self.numero} - {self.cliente.nombre}"
    
    def calcular_totales(self):
        """Calculate subtotal, tax and total from detail items."""
        detalles = self.detalles.all()
        self.subtotal = sum(d.subtotal for d in detalles)
        self.total_impuesto = sum(d.total_impuesto for d in detalles)
        self.total = self.subtotal + self.total_impuesto
        self.save()
    
    def generar_numero(self):
        """Generate a unique presupuesto number."""
        if not self.numero:
            last = Presupuesto.objects.filter(
                empresa=self.empresa
            ).order_by('-id').first()
            count = Presupuesto.objects.filter(empresa=self.empresa).count() + 1
            self.numero = f"PRES-{self.empresa.codigo}-{count:06d}"
        return self.numero


class PresupuestoDetalle(models.Model):
    """Line item in a presupuesto."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, null=True, blank=True)
    descripcion = models.CharField(max_length=255)  # Can override product name
    cantidad = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2)  # Editable price
    impuesto_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    
    # Extended prices (calculated)
    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_impuesto = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Order
    orden = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['orden']
        verbose_name = 'Detalle de Presupuesto'
        verbose_name_plural = 'Detalles de Presupuesto'
    
    def __str__(self):
        return f"{self.descripcion} x {self.cantidad}"
    
    def calcular_totales(self):
        """Calculate line totals."""
        self.subtotal = Decimal(self.cantidad) * Decimal(self.precio_unitario)
        self.total_impuesto = self.subtotal * (Decimal(self.impuesto_porcentaje) / Decimal(100))
        self.total = self.subtotal + self.total_impuesto
        self.save()
        # Recalculate parent
        self.presupuesto.calcular_totales()
