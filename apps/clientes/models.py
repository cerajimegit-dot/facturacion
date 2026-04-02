"""Cliente, DireccionCliente, ContactoCliente models."""
import uuid
from django.db import models
from apps.core.models import TenantModel, TenantManager


class Cliente(TenantModel):
    """Client record scoped to an empresa."""
    TIPO_CHOICES = [
        ('persona', 'Persona Física'),
        ('empresa', 'Empresa'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=255)
    ruc = models.CharField(max_length=30, blank=True, default='')
    telefono = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    direccion_facturacion = models.TextField(blank=True, default='')
    direccion_entrega = models.TextField(blank=True, default='')
    tipo_cliente = models.CharField(max_length=20, choices=TIPO_CHOICES, default='persona')
    sector = models.CharField(max_length=100, blank=True, default='')
    zona = models.CharField(max_length=100, blank=True, default='')
    observaciones = models.TextField(blank=True, default='')
    limite_credito = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)

    objects = TenantManager()

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        unique_together = ('empresa', 'ruc')

    def __str__(self):
        return f"{self.nombre} ({self.ruc})"


class DireccionCliente(models.Model):
    """Additional addresses for a client."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='direcciones')
    etiqueta = models.CharField(max_length=50, default='Principal')
    direccion = models.TextField()
    ciudad = models.CharField(max_length=100, blank=True, default='')
    departamento = models.CharField(max_length=100, blank=True, default='')
    pais = models.CharField(max_length=50, default='Paraguay')
    es_principal = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Dirección'
        verbose_name_plural = 'Direcciones'

    def __str__(self):
        return f"{self.etiqueta}: {self.direccion}"


class ContactoCliente(models.Model):
    """Contact person for a client."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='contactos')
    nombre = models.CharField(max_length=255)
    cargo = models.CharField(max_length=100, blank=True, default='')
    telefono = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    es_principal = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Contacto'
        verbose_name_plural = 'Contactos'

    def __str__(self):
        return self.nombre
