"""Custom User model and Membership (role per empresa)."""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.core.models import TimeStampedModel


class Usuario(AbstractUser):
    """Extended user model for the billing system."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    telefono = models.CharField(max_length=50, blank=True, default='')
    avatar = models.ImageField(upload_to='usuarios/avatars/', blank=True, null=True)
    idioma = models.CharField(max_length=5, default='es')
    zona_horaria = models.CharField(max_length=50, default='America/Asuncion')

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

    def __str__(self):
        return self.get_full_name() or self.username


class Membership(TimeStampedModel):
    """Maps a user to an empresa with a specific role."""
    ROL_CHOICES = [
        ('admin', 'Administrador'),
        ('vendedor', 'Vendedor'),
        ('contador', 'Contador'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        Usuario, on_delete=models.CASCADE, related_name='memberships'
    )
    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='memberships'
    )
    rol = models.CharField(max_length=20, choices=ROL_CHOICES, default='vendedor')
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('usuario', 'empresa')
        verbose_name = 'Membresía'
        verbose_name_plural = 'Membresías'

    def __str__(self):
        return f"{self.usuario} - {self.empresa} ({self.rol})"
