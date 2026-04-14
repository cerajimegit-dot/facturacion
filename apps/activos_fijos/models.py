"""Modelos del módulo de Activos Fijos."""
import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from apps.core.models import TenantModel, TenantManager


# ── Catálogos ─────────────────────────────────────────────────────────────────

class ClasificacionActivo(TenantModel):
    """Clasificación o categoría de activos fijos."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, default='')
    vida_util_default = models.PositiveIntegerField(
        default=5, help_text='Vida útil por defecto en años para esta clasificación'
    )

    # Cuentas contables por defecto para esta clasificación
    cuenta_activo = models.ForeignKey(
        'contabilidad.PlanCuentas', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='clasificaciones_activo',
        help_text='Cuenta de Activo Fijo (ej: 1.02.01)',
    )
    cuenta_depreciacion_acumulada = models.ForeignKey(
        'contabilidad.PlanCuentas', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='clasificaciones_dep_acum',
        help_text='Cuenta de Depreciación Acumulada (ej: 1.02.09)',
    )
    cuenta_gasto_depreciacion = models.ForeignKey(
        'contabilidad.PlanCuentas', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='clasificaciones_gasto_dep',
        help_text='Cuenta de Gasto por Depreciación (ej: 5.01.04)',
    )
    cuenta_resultado_baja = models.ForeignKey(
        'contabilidad.PlanCuentas', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='clasificaciones_res_baja',
        help_text='Cuenta de Resultado por Baja (ej: 4.02.01)',
    )

    objects = TenantManager()

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Clasificación de Activo'
        verbose_name_plural = 'Clasificaciones de Activos'
        unique_together = ('empresa', 'nombre')

    def __str__(self):
        return self.nombre


class UbicacionActivo(TenantModel):
    """Ubicación física donde se encuentran los activos."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    planta = models.CharField(max_length=100)
    edificio = models.CharField(max_length=100, blank=True, default='')
    area = models.CharField(max_length=100, blank=True, default='')

    objects = TenantManager()

    class Meta:
        ordering = ['planta', 'edificio', 'area']
        verbose_name = 'Ubicación'
        verbose_name_plural = 'Ubicaciones'
        unique_together = ('empresa', 'planta', 'edificio', 'area')

    def __str__(self):
        parts = [self.planta]
        if self.edificio:
            parts.append(self.edificio)
        if self.area:
            parts.append(self.area)
        return ' / '.join(parts)


class CentroCosto(TenantModel):
    """Centro de costo para asignación contable de activos."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=20)
    descripcion = models.TextField(blank=True, default='')

    objects = TenantManager()

    class Meta:
        ordering = ['codigo']
        verbose_name = 'Centro de Costo'
        verbose_name_plural = 'Centros de Costo'
        unique_together = ('empresa', 'codigo')

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


# ── Modelo Principal ──────────────────────────────────────────────────────────

class ActivoFijo(TenantModel):
    """Activo fijo de la empresa."""
    TIPO_CHOICES = [
        ('IT', 'IT / Tecnología'),
        ('planta', 'Planta / Maquinaria'),
        ('mobiliario', 'Mobiliario'),
        ('vehiculo', 'Vehículo'),
        ('edificio', 'Edificio'),
        ('terreno', 'Terreno'),
        ('otro', 'Otro'),
    ]
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('en_mantenimiento', 'En Mantenimiento'),
        ('baja', 'Dado de Baja'),
    ]
    MONEDA_CHOICES = [
        ('PYG', 'Guaraní'),
        ('USD', 'Dólar'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=50, db_index=True)
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, default='')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='otro')
    clasificacion = models.ForeignKey(
        ClasificacionActivo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='activos',
    )
    ubicacion = models.ForeignKey(
        UbicacionActivo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='activos',
    )
    centro_costo = models.ForeignKey(
        CentroCosto, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='activos',
    )
    moneda = models.CharField(max_length=3, choices=MONEDA_CHOICES, default='PYG')
    valor_adquisicion = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_residual = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text='Valor estimado al final de la vida útil'
    )
    fecha_adquisicion = models.DateField()
    fecha_activacion = models.DateField(
        null=True, blank=True,
        help_text='Fecha en la que el activo comenzó a depreciarse'
    )
    vida_util_anios = models.PositiveIntegerField(default=5)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    proveedor = models.ForeignKey(
        'compras.Proveedor', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='activos_fijos',
    )
    responsable = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='activos_asignados',
    )
    numero_serie = models.CharField(max_length=100, blank=True, default='')
    numero_factura = models.CharField(max_length=50, blank=True, default='')
    imagen = models.ImageField(upload_to='activos_fijos/', blank=True, null=True)
    notas = models.TextField(blank=True, default='')
    propiedad_terceros = models.BooleanField(
        default=False,
        help_text='Bienes en admisión temporaria/maquila — no deprecian ni van al balance',
    )

    # Cuentas contables (override de la clasificación)
    cuenta_activo = models.ForeignKey(
        'contabilidad.PlanCuentas', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='activos_fijos_cuenta',
        help_text='Override: Cuenta de Activo Fijo',
    )
    cuenta_depreciacion_acumulada = models.ForeignKey(
        'contabilidad.PlanCuentas', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='activos_fijos_dep_acum',
        help_text='Override: Cuenta de Depreciación Acumulada',
    )
    cuenta_gasto_depreciacion = models.ForeignKey(
        'contabilidad.PlanCuentas', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='activos_fijos_gasto_dep',
        help_text='Override: Cuenta de Gasto por Depreciación',
    )

    # Campos calculados de depreciación
    depreciacion_acumulada = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_libro = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    objects = TenantManager()

    class Meta:
        ordering = ['codigo']
        verbose_name = 'Activo Fijo'
        verbose_name_plural = 'Activos Fijos'
        unique_together = ('empresa', 'codigo')

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    def save(self, *args, **kwargs):
        if not self.fecha_activacion:
            self.fecha_activacion = self.fecha_adquisicion
        self.valor_libro = self.valor_adquisicion - self.depreciacion_acumulada
        super().save(*args, **kwargs)

    def get_cuenta_activo(self):
        """Cuenta de activo: override del activo > default de clasificación."""
        return self.cuenta_activo or (self.clasificacion.cuenta_activo if self.clasificacion else None)

    def get_cuenta_dep_acumulada(self):
        """Cuenta de dep. acumulada: override del activo > default de clasificación."""
        return self.cuenta_depreciacion_acumulada or (
            self.clasificacion.cuenta_depreciacion_acumulada if self.clasificacion else None)

    def get_cuenta_gasto_dep(self):
        """Cuenta de gasto depreciación: override del activo > default de clasificación."""
        return self.cuenta_gasto_depreciacion or (
            self.clasificacion.cuenta_gasto_depreciacion if self.clasificacion else None)

    def get_cuenta_resultado_baja(self):
        """Cuenta de resultado por baja: solo de clasificación."""
        return self.clasificacion.cuenta_resultado_baja if self.clasificacion else None

    @property
    def depreciacion_mensual(self):
        """Depreciación mensual lineal."""
        if self.vida_util_anios <= 0:
            return Decimal('0')
        base = self.valor_adquisicion - self.valor_residual
        return (base / (self.vida_util_anios * 12)).quantize(Decimal('0.01'))

    @property
    def depreciacion_anual(self):
        """Depreciación anual lineal."""
        if self.vida_util_anios <= 0:
            return Decimal('0')
        base = self.valor_adquisicion - self.valor_residual
        return (base / self.vida_util_anios).quantize(Decimal('0.01'))

    @property
    def porcentaje_depreciado(self):
        """Porcentaje de depreciación acumulada."""
        if self.valor_adquisicion <= 0:
            return Decimal('0')
        return ((self.depreciacion_acumulada / self.valor_adquisicion) * 100).quantize(Decimal('0.01'))

    @property
    def vida_util_restante_meses(self):
        """Meses restantes de vida útil."""
        if not self.fecha_activacion or self.vida_util_anios <= 0:
            return 0
        from dateutil.relativedelta import relativedelta
        fecha_fin = self.fecha_activacion + relativedelta(years=self.vida_util_anios)
        hoy = timezone.now().date()
        if hoy >= fecha_fin:
            return 0
        delta = relativedelta(fecha_fin, hoy)
        return delta.years * 12 + delta.months

    @property
    def esta_totalmente_depreciado(self):
        """Si ya alcanzó la depreciación total."""
        return self.depreciacion_acumulada >= (self.valor_adquisicion - self.valor_residual)

    @property
    def supera_vida_util(self):
        """Si el activo superó su vida útil sin darse de baja."""
        if not self.fecha_activacion or self.estado == 'baja':
            return False
        from dateutil.relativedelta import relativedelta
        fecha_fin = self.fecha_activacion + relativedelta(years=self.vida_util_anios)
        return timezone.now().date() > fecha_fin


# ── Historial y Movimientos ───────────────────────────────────────────────────

class MovimientoActivo(TenantModel):
    """Registro de movimientos/transferencias de un activo entre ubicaciones."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activo = models.ForeignKey(
        ActivoFijo, on_delete=models.CASCADE, related_name='movimientos'
    )
    fecha = models.DateTimeField(default=timezone.now)
    ubicacion_origen = models.ForeignKey(
        UbicacionActivo, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='movimientos_salida',
    )
    ubicacion_destino = models.ForeignKey(
        UbicacionActivo, on_delete=models.SET_NULL, null=True,
        related_name='movimientos_entrada',
    )
    responsable_anterior = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='movimientos_entregados',
    )
    responsable_nuevo = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='movimientos_recibidos',
    )
    motivo = models.TextField(blank=True, default='')
    usuario_registro = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True,
        related_name='movimientos_activo_registrados',
    )

    objects = TenantManager()

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Movimiento de Activo'
        verbose_name_plural = 'Movimientos de Activos'

    def __str__(self):
        return f"{self.activo.codigo}: {self.ubicacion_origen} → {self.ubicacion_destino}"


class MantenimientoActivo(TenantModel):
    """Registro de mantenimientos preventivos y correctivos."""
    TIPO_CHOICES = [
        ('preventivo', 'Preventivo'),
        ('correctivo', 'Correctivo'),
    ]
    ESTADO_CHOICES = [
        ('programado', 'Programado'),
        ('en_proceso', 'En Proceso'),
        ('completado', 'Completado'),
        ('cancelado', 'Cancelado'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activo = models.ForeignKey(
        ActivoFijo, on_delete=models.CASCADE, related_name='mantenimientos'
    )
    fecha = models.DateTimeField(default=timezone.now)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES, default='preventivo')
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='programado')
    descripcion = models.TextField(blank=True, default='')
    costo = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    proveedor_servicio = models.CharField(max_length=255, blank=True, default='')
    usuario = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='mantenimientos_registrados',
    )

    objects = TenantManager()

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Mantenimiento de Activo'
        verbose_name_plural = 'Mantenimientos de Activos'

    def __str__(self):
        return f"{self.activo.codigo} - {self.get_tipo_display()} ({self.fecha.strftime('%Y-%m-%d')})"


class BajaActivo(TenantModel):
    """Registro de baja/desincorporación de un activo."""
    MOTIVO_CHOICES = [
        ('obsolescencia', 'Obsolescencia'),
        ('daño_irreparable', 'Daño Irreparable'),
        ('venta', 'Venta'),
        ('donacion', 'Donación'),
        ('robo', 'Robo/Pérdida'),
        ('otro', 'Otro'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activo = models.OneToOneField(
        ActivoFijo, on_delete=models.CASCADE, related_name='baja'
    )
    fecha_baja = models.DateField()
    motivo = models.CharField(max_length=20, choices=MOTIVO_CHOICES, default='obsolescencia')
    motivo_detalle = models.TextField(blank=True, default='')
    valor_rescate = models.DecimalField(
        max_digits=15, decimal_places=2, default=0,
        help_text='Valor obtenido por venta o rescate'
    )
    usuario = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True,
        related_name='bajas_registradas',
    )
    autorizado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='bajas_autorizadas',
    )

    objects = TenantManager()

    class Meta:
        ordering = ['-fecha_baja']
        verbose_name = 'Baja de Activo'
        verbose_name_plural = 'Bajas de Activos'

    def __str__(self):
        return f"Baja: {self.activo.codigo} ({self.fecha_baja})"


class DepreciacionMensual(TenantModel):
    """Registro mensual de depreciación calculada."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    activo = models.ForeignKey(
        ActivoFijo, on_delete=models.CASCADE, related_name='depreciaciones'
    )
    anio = models.PositiveIntegerField()
    mes = models.PositiveIntegerField()
    monto = models.DecimalField(max_digits=15, decimal_places=2)
    depreciacion_acumulada = models.DecimalField(max_digits=15, decimal_places=2)
    valor_libro = models.DecimalField(max_digits=15, decimal_places=2)

    objects = TenantManager()

    class Meta:
        ordering = ['anio', 'mes']
        verbose_name = 'Depreciación Mensual'
        verbose_name_plural = 'Depreciaciones Mensuales'
        unique_together = ('empresa', 'activo', 'anio', 'mes')

    def __str__(self):
        return f"{self.activo.codigo} - {self.anio}/{self.mes:02d}: {self.monto}"


class ProcesoDepreciacion(TenantModel):
    """Control de ejecución del batch de depreciación mensual."""
    ESTADO_CHOICES = [
        ('en_proceso', 'En Proceso'),
        ('completado', 'Completado'),
        ('error', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    anio = models.PositiveIntegerField()
    mes = models.PositiveIntegerField()
    estado = models.CharField(max_length=15, choices=ESTADO_CHOICES, default='en_proceso')
    activos_procesados = models.PositiveIntegerField(default=0)
    activos_con_error = models.PositiveIntegerField(default=0)
    registros_creados = models.PositiveIntegerField(default=0)
    asiento = models.OneToOneField(
        'contabilidad.Asiento', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='proceso_depreciacion',
        help_text='Asiento contable generado por este proceso',
    )
    usuario = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='procesos_depreciacion',
    )
    notas = models.TextField(blank=True, default='')
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)

    objects = TenantManager()

    class Meta:
        ordering = ['-anio', '-mes']
        verbose_name = 'Proceso de Depreciación'
        verbose_name_plural = 'Procesos de Depreciación'
        unique_together = ('empresa', 'anio', 'mes')

    def __str__(self):
        return f"Depreciación {self.mes:02d}/{self.anio} — {self.estado}"
