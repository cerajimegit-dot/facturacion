"""Producto, Variante, PrecioLista, Categoria models."""
import uuid
from django.db import models
from apps.core.models import TenantModel, TenantManager


class Categoria(TenantModel):
    """Product category scoped to empresa."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, default='')
    padre = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='subcategorias',
    )

    objects = TenantManager()

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        unique_together = ('empresa', 'nombre')

    def __str__(self):
        return self.nombre


class Producto(TenantModel):
    """Product or service record."""
    TIPO_CHOICES = [
        ('producto', 'Producto'),
        ('servicio', 'Servicio'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sku = models.CharField(max_length=50, db_index=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, default='')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='producto')
    categoria = models.ForeignKey(
        Categoria, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='productos',
    )
    precio_unitario = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    costo = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    moneda = models.CharField(max_length=3, default='PYG')
    impuesto_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=10)
    imagen_url = models.URLField(blank=True, default='')
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    
    # Contabilidad
    cuenta_contable = models.ForeignKey(
        'contabilidad.PlanCuentas',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='productos',
        help_text="Cuenta contable para contabilizar compras de este producto"
    )
    
    activo = models.BooleanField(default=True)

    objects = TenantManager()

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        unique_together = ('empresa', 'sku')

    def __str__(self):
        return f"{self.sku} - {self.nombre}"


class Variante(models.Model):
    """Product variant (size, color, etc.)."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='variantes')
    nombre = models.CharField(max_length=100)
    sku_variante = models.CharField(max_length=50, blank=True, default='')
    precio_diferencial = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        verbose_name = 'Variante'
        verbose_name_plural = 'Variantes'

    def __str__(self):
        return f"{self.producto.sku} / {self.nombre}"


class PrecioLista(TenantModel):
    """Price list for different customer segments."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='precios_lista')
    precio = models.DecimalField(max_digits=15, decimal_places=2)
    moneda = models.CharField(max_length=3, default='PYG')
    vigente_desde = models.DateField(null=True, blank=True)
    vigente_hasta = models.DateField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        verbose_name = 'Precio de Lista'
        verbose_name_plural = 'Precios de Lista'

    def __str__(self):
        return f"{self.nombre}: {self.producto.sku} @ {self.precio}"
