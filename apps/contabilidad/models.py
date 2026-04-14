"""Modelos para el módulo de contabilidad."""
import uuid
from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator
from apps.core.models import TenantModel, TenantManager


class PlanCuentas(TenantModel):
    """Plan de cuentas contables de la empresa."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificadores
    codigo_cuenta = models.CharField(
        max_length=20,
        db_index=True,
        help_text="Código completo de la cuenta (ej: 1410, 2110)"
    )
    codigo_reducido = models.CharField(
        max_length=10,
        blank=True,
        help_text="Código reducido para reportes"
    )
    
    # Descripción
    descripcion = models.CharField(max_length=255)
    
    # Naturaleza de la cuenta
    CONDICION_CHOICES = [
        ('deudora', 'Cuenta Deudora'),
        ('acreedora', 'Cuenta Acreedora'),
    ]
    condicion = models.CharField(
        max_length=10,
        choices=CONDICION_CHOICES,
        help_text="Naturaleza de la cuenta (deudora o acreedora)"
    )
    
    # Tipo de cuenta
    CLASE_CHOICES = [
        ('sintetica', '1 - Sintética (Agrupadora)'),
        ('analitica', '2 - Analítica (Detalle)'),
    ]
    clase = models.CharField(
        max_length=10,
        choices=CLASE_CHOICES,
        default='analitica',
        help_text="Tipo de cuenta: sintética (agrupa) o analítica (detalle)"
    )
    
    # Capacidades
    acepta_item = models.BooleanField(
        default=False,
        help_text="Permite asignar ítems contables (P||RUC)"
    )
    acepta_centro_costo = models.BooleanField(
        default=False,
        help_text="Permite asignar centro de costo"
    )
    acepta_nivel = models.BooleanField(
        default=False,
        help_text="Permite asignar nivel (clvl)"
    )
    
    # Auditoría
    activa = models.BooleanField(default=True, db_index=True)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name='subcuentas',
        help_text="Cuenta padre (para cuentas sintéticas)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = TenantManager()
    
    class Meta:
        ordering = ['codigo_cuenta']
        verbose_name = 'Cuenta Contable'
        verbose_name_plural = 'Plan de Cuentas'
        unique_together = ('empresa', 'codigo_cuenta')
        indexes = [
            models.Index(fields=['empresa', 'codigo_cuenta']),
            models.Index(fields=['empresa', 'activa']),
        ]
    
    def __str__(self):
        return f"{self.codigo_cuenta} - {self.descripcion}"


class CotizacionDiaria(models.Model):
    """Cotización diaria de monedas (USD/PYG)."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    empresa = models.ForeignKey(
        'empresas.Empresa',
        on_delete=models.PROTECT,
        related_name='cotizaciones_diarias'
    )
    fecha = models.DateField(db_index=True)
    
    # Cotización
    moneda_origen = models.CharField(
        max_length=3,
        default='USD',
        help_text="Moneda a convertir (ej: USD)"
    )
    moneda_destino = models.CharField(
        max_length=3,
        default='PYG',
        help_text="Moneda destino (ej: PYG)"
    )
    tasa = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Tasa de cambio (ej: 5200.00 PYG por 1 USD)"
    )
    
    # Auditoría
    usuario_carga = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='cotizaciones_cargadas'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha', 'moneda_origen', 'moneda_destino']
        unique_together = ('empresa', 'fecha', 'moneda_origen', 'moneda_destino')
        verbose_name = 'Cotización Diaria'
        verbose_name_plural = 'Cotizaciones Diarias'
    
    def __str__(self):
        return f"1 {self.moneda_origen} = {self.tasa} {self.moneda_destino} ({self.fecha})"


class Asiento(TenantModel):
    """Asiento contable."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identificación
    numero_asiento = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Número correlativo del asiento"
    )
    tipo_asiento = models.CharField(
        max_length=50,
        db_index=True,
        help_text="Tipo de asiento (COMPRA, VENTA, AJUSTE, etc)"
    )
    
    fecha = models.DateField(db_index=True)
    descripcion = models.TextField()
    
    # Referencias
    compra = models.OneToOneField(
        'compras.Compra',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='asiento_contable',
        help_text="Compra que generó este asiento"
    )
    venta = models.OneToOneField(
        'ventas.Venta',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='asiento_contable',
        help_text="Venta que generó este asiento"
    )
    gasto = models.ForeignKey(
        'compras.Gasto',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='asientos_contables',
        help_text="Gasto que generó este asiento"
    )
    
    # Moneda
    moneda = models.CharField(
        max_length=3,
        default='PYG',
        choices=[('PYG', 'Guaraní'), ('USD', 'Dólar')],
        db_index=True
    )
    
    # Totales
    total_debe = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )
    total_haber = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )
    
    # Estado
    estado = models.CharField(
        max_length=20,
        choices=[
            ('borrador', 'Borrador'),
            ('registrado', 'Registrado'),
            ('reversado', 'Reversado'),
        ],
        default='borrador',
        db_index=True
    )
    
    # Auditoría
    usuario_crea = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='asientos_creados'
    )
    fecha_registro = models.DateTimeField(null=True, blank=True)
    usuario_registra = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asientos_registrados'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = TenantManager()
    
    class Meta:
        ordering = ['-fecha', '-numero_asiento']
        verbose_name = 'Asiento Contable'
        verbose_name_plural = 'Asientos Contables'
        unique_together = ('empresa', 'numero_asiento')
        indexes = [
            models.Index(fields=['empresa', 'tipo_asiento', 'fecha']),
            models.Index(fields=['empresa', 'estado']),
        ]
    
    def __str__(self):
        return f"Asiento {self.numero_asiento} ({self.tipo_asiento}) - {self.fecha}"
    
    def validate_balance(self):
        """Validar que debe = haber."""
        if self.total_debe != self.total_haber:
            raise ValueError(
                f"Asiento desbalanceado: Debe={self.total_debe}, Haber={self.total_haber}"
            )
    
    def registrar(self, usuario):
        """Registrar el asiento contable."""
        from django.utils import timezone
        self.validate_balance()
        self.estado = 'registrado'
        self.usuario_registra = usuario
        self.fecha_registro = timezone.now()
        self.save()


class LineaAsiento(TenantModel):
    """Línea individual de un asiento contable."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    asiento = models.ForeignKey(
        Asiento,
        on_delete=models.CASCADE,
        related_name='lineas'
    )
    
    # Cuenta contable
    cuenta = models.ForeignKey(
        PlanCuentas,
        on_delete=models.PROTECT,
        related_name='lineas_asiento'
    )
    
    # Montos
    debe = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    haber = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(Decimal('0'))]
    )
    
    # Detalles
    observacion = models.CharField(
        max_length=255,
        blank=True,
        help_text="Observación de línea (ej: P800190432 para item contable)"
    )
    item_contable = models.CharField(
        max_length=50,
        blank=True,
        help_text="Ítem contable (P + RUC o código único)"
    )
    centro_costo = models.CharField(
        max_length=50,
        blank=True,
        help_text="Centro de costo"
    )
    nivel = models.CharField(
        max_length=50,
        blank=True,
        help_text="Nivel"
    )
    
    # Referencia
    compra_detalle = models.ForeignKey(
        'compras.CompraDetalle',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lineas_asiento'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = TenantManager()
    
    class Meta:
        ordering = ['asiento', 'id']
        verbose_name = 'Línea de Asiento'
        verbose_name_plural = 'Líneas de Asiento'
        indexes = [
            models.Index(fields=['asiento', 'cuenta']),
        ]
    
    def __str__(self):
        return f"Línea {self.id} - {self.cuenta.codigo_cuenta}"
    
    def clean(self):
        """Validar que solo una de debe/haber sea > 0."""
        if self.debe > 0 and self.haber > 0:
            raise ValueError("Una línea no puede tener debe y haber simultáneamente")
        if self.debe == 0 and self.haber == 0:
            raise ValueError("Una línea debe tener debe o haber > 0")


class SaldoCuenta(TenantModel):
    """Saldo acumulado de cada cuenta contable (para auditoría)."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    cuenta = models.ForeignKey(
        PlanCuentas,
        on_delete=models.CASCADE,
        related_name='saldos'
    )
    fecha = models.DateField(db_index=True)
    
    saldo_anterior = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )
    movimiento_debe = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )
    movimiento_haber = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )
    saldo_actual = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        default=0
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = TenantManager()
    
    class Meta:
        ordering = ['cuenta', '-fecha']
        verbose_name = 'Saldo de Cuenta'
        verbose_name_plural = 'Saldos de Cuentas'
        unique_together = ('empresa', 'cuenta', 'fecha')
    
    def __str__(self):
        return f"{self.cuenta.codigo_cuenta} - {self.fecha} = {self.saldo_actual}"
