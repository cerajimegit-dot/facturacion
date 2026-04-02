"""Audit trail model."""
import uuid
from django.db import models


class Auditoria(models.Model):
    """Logs all create/update/delete actions by users."""
    ACCION_CHOICES = [
        ('crear', 'Crear'),
        ('actualizar', 'Actualizar'),
        ('eliminar', 'Eliminar'),
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('importar', 'Importar'),
        ('exportar', 'Exportar'),
        ('aprobar', 'Aprobar'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='acciones_auditoria',
    )
    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='acciones_auditoria',
    )
    accion = models.CharField(max_length=20, choices=ACCION_CHOICES)
    modelo = models.CharField(max_length=100)
    objeto_id = models.CharField(max_length=255, blank=True, default='')
    datos_anteriores = models.JSONField(null=True, blank=True)
    datos_nuevos = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    descripcion = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Registro de Auditoría'
        verbose_name_plural = 'Registros de Auditoría'
        indexes = [
            models.Index(fields=['usuario', 'timestamp']),
            models.Index(fields=['empresa', 'timestamp']),
            models.Index(fields=['modelo', 'objeto_id']),
        ]

    def __str__(self):
        return f"{self.timestamp} | {self.usuario} | {self.accion} {self.modelo}"
