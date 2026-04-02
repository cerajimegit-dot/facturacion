"""Pago model for payment tracking."""
import uuid
from django.db import models
from apps.core.models import TenantModel, TenantManager


class Pago(TenantModel):
    """Payment record linked to a sale."""
    METODO_CHOICES = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia Bancaria'),
        ('tarjeta', 'Tarjeta'),
        ('cheque', 'Cheque'),
        ('otro', 'Otro'),
    ]
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('rechazado', 'Rechazado'),
        ('anulado', 'Anulado'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    venta = models.ForeignKey(
        'ventas.Venta', on_delete=models.CASCADE, related_name='pagos'
    )
    cliente = models.ForeignKey(
        'clientes.Cliente', on_delete=models.CASCADE, related_name='pagos'
    )
    fecha = models.DateField()
    monto = models.DecimalField(max_digits=15, decimal_places=2)
    moneda = models.CharField(max_length=3, default='PYG')
    metodo = models.CharField(max_length=20, choices=METODO_CHOICES, default='efectivo')
    referencia = models.CharField(max_length=100, blank=True, default='')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    notas = models.TextField(blank=True, default='')
    comprobante = models.FileField(upload_to='pagos/comprobantes/', blank=True, null=True)
    registrado_por = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True,
    )

    objects = TenantManager()

    class Meta:
        ordering = ['-fecha']
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'

    def __str__(self):
        return f"Pago {self.monto} {self.moneda} - VTA {self.venta.numero}"
