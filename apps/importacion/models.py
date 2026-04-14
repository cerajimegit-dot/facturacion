"""Models for tracking import jobs and their results."""
import uuid
from django.db import models
from apps.core.models import TimeStampedModel


class ImportJob(TimeStampedModel):
    """Tracks an Excel import job through its lifecycle."""
    ESTADO_CHOICES = [
        ('subido', 'Archivo Subido'),
        ('validando', 'Validando'),
        ('validado', 'Validación Completa'),
        ('importando', 'Importando'),
        ('completado', 'Completado'),
        ('error', 'Error'),
        ('cancelado', 'Cancelado'),
    ]
    TIPO_CHOICES = [
        ('clientes', 'Clientes'),
        ('productos', 'Productos'),
        ('stock', 'Stock'),
        ('ventas', 'Ventas'),
        ('compras', 'Compras'),
        ('activos_fijos', 'Activos Fijos'),
        ('mixto', 'Mixto (múltiples hojas)'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='import_jobs'
    )
    usuario = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True,
    )
    archivo = models.FileField(upload_to='importaciones/')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='subido')
    # Validation results
    total_filas = models.IntegerField(default=0)
    filas_validas = models.IntegerField(default=0)
    filas_warnings = models.IntegerField(default=0)
    filas_errores = models.IntegerField(default=0)
    filas_importadas = models.IntegerField(default=0)
    reporte_validacion = models.JSONField(null=True, blank=True)
    reporte_errores = models.JSONField(null=True, blank=True)
    archivo_errores = models.FileField(
        upload_to='importaciones/errores/', blank=True, null=True
    )
    # Celery task tracking
    task_id = models.CharField(max_length=255, blank=True, default='')
    mensaje = models.TextField(blank=True, default='')
    iniciado_en = models.DateTimeField(null=True, blank=True)
    finalizado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Trabajo de Importación'
        verbose_name_plural = 'Trabajos de Importación'

    def __str__(self):
        return f"Import {self.tipo} - {self.estado} ({self.id})"
