"""Custom User model and Membership (role per empresa)."""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from apps.core.models import TimeStampedModel


# Módulos disponibles en el sistema
MODULOS_DISPONIBLES = [
    ("dashboard", "📈 Dashboard"),
    ("empresas", "🏢 Empresas"),
    ("usuarios", "👥 Usuarios"),
    ("clientes", "👥 Clientes"),
    ("productos", "📦 Productos"),
    ("inventario", "🏭 Inventario"),
    ("ventas", "🧾 Ventas"),
    ("cobros", "💳 Cobros Parciales"),
    ("compras", "🛒 Compras"),
    ("gastos_dashboard", "📊 Dashboard Gastos"),
    ("presupuestos", "📋 Presupuestos"),
    ("pagos", "💰 Pagos"),
    ("contabilidad", "📋 Contabilidad"),
    ("importacion", "📥 Importación Excel"),
    ("reportes", "📊 Reportes"),
    ("auditoria", "🔍 Auditoría"),
]

# Accesos por defecto según rol
ACCESOS_DEFAULT = {
    "admin": [m[0] for m in MODULOS_DISPONIBLES],  # admin accede a todo
    "contador": [
        "dashboard", "compras", "gastos_dashboard", "pagos",
        "contabilidad", "reportes", "productos", "inventario",
    ],
    "vendedor": [
        "dashboard", "clientes", "productos", "ventas",
        "cobros", "presupuestos", "reportes",
    ],
}


class Usuario(AbstractUser):
    """Extended user model for the billing system."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='usuarios',
        null=True, blank=True, help_text='Empresa a la que pertenece el usuario'
    )
    rol = models.CharField(
        max_length=20, 
        choices=[('admin', 'Administrador'), ('vendedor', 'Vendedor'), ('contador', 'Contador')],
        default='vendedor',
        help_text='Rol dentro de su empresa'
    )
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


class ConfiguracionAcceso(TimeStampedModel):
    """Configura qué módulos puede acceder cada rol en una empresa."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        'empresas.Empresa', on_delete=models.CASCADE, related_name='config_accesos'
    )
    rol = models.CharField(max_length=20, choices=Membership.ROL_CHOICES)
    modulos_permitidos = models.JSONField(
        default=list,
        help_text="Lista de módulos permitidos para este rol"
    )

    class Meta:
        unique_together = ('empresa', 'rol')
        verbose_name = 'Configuración de Acceso'
        verbose_name_plural = 'Configuraciones de Acceso'

    def __str__(self):
        return f"{self.empresa} - {self.rol}: {len(self.modulos_permitidos)} módulos"

    @classmethod
    def get_modulos_permitidos(cls, empresa, rol):
        """Obtener módulos permitidos. Si no hay config, usar defaults."""
        if rol == 'admin':
            return [m[0] for m in MODULOS_DISPONIBLES]
        try:
            config = cls.objects.get(empresa=empresa, rol=rol)
            return config.modulos_permitidos
        except cls.DoesNotExist:
            return ACCESOS_DEFAULT.get(rol, [])
