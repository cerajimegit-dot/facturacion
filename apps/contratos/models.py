"""Contrato and OrdenServicio models."""
import uuid
from django.db import models
from apps.core.models import TenantModel, TenantManager


class Contrato(TenantModel):
    """Maintenance / service contract."""
    ESTADO_CHOICES = [
        ('borrador', 'Borrador'),
        ('activo', 'Activo'),
        ('suspendido', 'Suspendido'),
        ('finalizado', 'Finalizado'),
        ('cancelado', 'Cancelado'),
    ]
    FRECUENCIA_CHOICES = [
        ('mensual', 'Mensual'),
        ('trimestral', 'Trimestral'),
        ('semestral', 'Semestral'),
        ('anual', 'Anual'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=30, db_index=True)
    cliente = models.ForeignKey(
        'clientes.Cliente', on_delete=models.CASCADE, related_name='contratos'
    )
    descripcion = models.TextField(blank=True, default='')
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='borrador')
    monto_recurrente = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    moneda = models.CharField(max_length=3, default='PYG')
    frecuencia_cobro = models.CharField(
        max_length=20, choices=FRECUENCIA_CHOICES, default='mensual'
    )
    terminos = models.TextField(blank=True, default='')
    notas = models.TextField(blank=True, default='')

    objects = TenantManager()

    class Meta:
        ordering = ['-fecha_inicio']
        verbose_name = 'Contrato'
        verbose_name_plural = 'Contratos'
        unique_together = ('empresa', 'numero')

    def __str__(self):
        return f"CTR-{self.numero} - {self.cliente.nombre}"


class OrdenServicio(TenantModel):
    """Service order linked to a contract or standalone."""
    ESTADO_CHOICES = [
        ('abierta', 'Abierta'),
        ('en_progreso', 'En Progreso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]
    PRIORIDAD_CHOICES = [
        ('baja', 'Baja'),
        ('media', 'Media'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.CharField(max_length=30, db_index=True)
    contrato = models.ForeignKey(
        Contrato, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ordenes_servicio',
    )
    cliente = models.ForeignKey(
        'clientes.Cliente', on_delete=models.CASCADE, related_name='ordenes_servicio'
    )
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='abierta')
    prioridad = models.CharField(max_length=20, choices=PRIORIDAD_CHOICES, default='media')
    fecha_programada = models.DateField(null=True, blank=True)
    fecha_completada = models.DateField(null=True, blank=True)
    asignado_a = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
    )
    notas = models.TextField(blank=True, default='')

    objects = TenantManager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Orden de Servicio'
        verbose_name_plural = 'Órdenes de Servicio'
        unique_together = ('empresa', 'numero')

    def __str__(self):
        return f"OS-{self.numero}"
