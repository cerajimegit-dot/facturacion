"""Empresa (tenant) model."""
import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class Empresa(TimeStampedModel):
    """Each empresa is a tenant. All business data is scoped to an empresa."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=20, unique=True, db_index=True)
    nombre = models.CharField(max_length=255)
    ruc = models.CharField(max_length=30, blank=True, default='')
    razon_social = models.CharField(max_length=255, blank=True, default='')
    direccion = models.TextField(blank=True, default='')
    telefono = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    logo = models.ImageField(upload_to='empresas/logos/', blank=True, null=True)
    moneda_principal = models.CharField(
        max_length=3, default='PYG',
        choices=[('PYG', 'Guaraní'), ('USD', 'Dólar')]
    )
    activa = models.BooleanField(default=True)
    configuracion = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
