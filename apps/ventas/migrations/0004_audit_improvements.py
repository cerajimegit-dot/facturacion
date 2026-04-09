# Migration for audit improvements
# - Add condicion_iva to LineaVenta, LineaCotizacion
# - Convert LineaVenta, LineaCotizacion to TenantModel (add empresa, timestamps)
# - Add tipo_comprobante to Venta
# - Add 'anulada' to CuentaPorCobrar estado
# - Add NotaCredito and LineaNotaCredito models

import uuid
import django.db.models.deletion
import django.core.validators
from decimal import Decimal
from django.db import migrations, models
from django.utils import timezone


def populate_empresa_from_parent(apps, schema_editor):
    """Set empresa on LineaVenta from its venta, and LineaCotizacion from its cotizacion."""
    LineaVenta = apps.get_model('ventas', 'LineaVenta')
    for linea in LineaVenta.objects.select_related('venta').all():
        if linea.venta_id and not linea.empresa_id:
            linea.empresa_id = linea.venta.empresa_id
            linea.save(update_fields=['empresa_id'])

    LineaCotizacion = apps.get_model('ventas', 'LineaCotizacion')
    for linea in LineaCotizacion.objects.select_related('cotizacion').all():
        if linea.cotizacion_id and not linea.empresa_id:
            linea.empresa_id = linea.cotizacion.empresa_id
            linea.save(update_fields=['empresa_id'])


class Migration(migrations.Migration):

    dependencies = [
        ('empresas', '0001_initial'),
        ('ventas', '0003_alter_registropago_empresa'),
        ('productos', '0001_initial'),
        ('clientes', '0001_initial'),
    ]

    operations = [
        # ── Add condicion_iva to LineaVenta ──
        migrations.AddField(
            model_name='lineaventa',
            name='condicion_iva',
            field=models.CharField(
                choices=[('gravada_10', 'Gravada 10%'), ('gravada_5', 'Gravada 5%'), ('exenta', 'Exenta')],
                default='gravada_10',
                help_text='Condición de IVA según Ley 6380/19',
                max_length=15,
            ),
        ),

        # ── Add empresa FK to LineaVenta (nullable first) ──
        migrations.AddField(
            model_name='lineaventa',
            name='empresa',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='lineaventa_set',
                to='empresas.empresa',
            ),
        ),

        # ── Add timestamps to LineaVenta ──
        migrations.AddField(
            model_name='lineaventa',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='lineaventa',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),

        # ── Add condicion_iva to LineaCotizacion ──
        migrations.AddField(
            model_name='lineacotizacion',
            name='condicion_iva',
            field=models.CharField(
                choices=[('gravada_10', 'Gravada 10%'), ('gravada_5', 'Gravada 5%'), ('exenta', 'Exenta')],
                default='gravada_10',
                help_text='Condición de IVA según Ley 6380/19',
                max_length=15,
            ),
        ),

        # ── Add empresa FK to LineaCotizacion (nullable first) ──
        migrations.AddField(
            model_name='lineacotizacion',
            name='empresa',
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='lineacotizacion_set',
                to='empresas.empresa',
            ),
        ),

        # ── Add timestamps to LineaCotizacion ──
        migrations.AddField(
            model_name='lineacotizacion',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='lineacotizacion',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),

        # ── Populate empresa from parent objects ──
        migrations.RunPython(populate_empresa_from_parent, migrations.RunPython.noop),

        # ── Make empresa non-nullable on LineaVenta ──
        migrations.AlterField(
            model_name='lineaventa',
            name='empresa',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='%(class)s_set',
                to='empresas.empresa',
                db_index=True,
            ),
        ),

        # ── Make empresa non-nullable on LineaCotizacion ──
        migrations.AlterField(
            model_name='lineacotizacion',
            name='empresa',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='%(class)s_set',
                to='empresas.empresa',
                db_index=True,
            ),
        ),

        # ── Add tipo_comprobante to Venta ──
        migrations.AddField(
            model_name='venta',
            name='tipo_comprobante',
            field=models.CharField(
                choices=[('factura', 'Factura'), ('nota_credito', 'Nota de Crédito'), ('nota_debito', 'Nota de Débito'), ('autofactura', 'Autofactura')],
                default='factura',
                help_text='Tipo de comprobante fiscal',
                max_length=20,
            ),
        ),

        # ── Create NotaCredito model ──
        migrations.CreateModel(
            name='NotaCredito',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('empresa', models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_set', to='empresas.empresa')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('numero', models.CharField(db_index=True, max_length=30)),
                ('fecha', models.DateField()),
                ('motivo', models.CharField(choices=[('devolucion', 'Devolución de mercadería'), ('descuento', 'Descuento posterior'), ('bonificacion', 'Bonificación'), ('error_facturacion', 'Error de facturación'), ('otro', 'Otro')], max_length=20)),
                ('descripcion', models.TextField(blank=True, default='')),
                ('subtotal', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('impuestos', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('estado', models.CharField(choices=[('borrador', 'Borrador'), ('confirmada', 'Confirmada'), ('anulada', 'Anulada')], default='borrador', max_length=20)),
                ('venta_original', models.ForeignKey(help_text='Factura original que se corrige', on_delete=django.db.models.deletion.PROTECT, related_name='notas_credito', to='ventas.venta')),
                ('cliente', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='notas_credito', to='clientes.cliente')),
            ],
            options={
                'verbose_name': 'Nota de Crédito',
                'verbose_name_plural': 'Notas de Crédito',
                'ordering': ['-fecha', '-numero'],
                'unique_together': {('empresa', 'numero')},
            },
        ),

        # ── Create LineaNotaCredito model ──
        migrations.CreateModel(
            name='LineaNotaCredito',
            fields=[
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('empresa', models.ForeignKey(db_index=True, on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_set', to='empresas.empresa')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('descripcion', models.CharField(blank=True, default='', max_length=255)),
                ('cantidad', models.DecimalField(decimal_places=2, max_digits=15)),
                ('precio_unitario', models.DecimalField(decimal_places=2, max_digits=15)),
                ('condicion_iva', models.CharField(choices=[('gravada_10', 'Gravada 10%'), ('gravada_5', 'Gravada 5%'), ('exenta', 'Exenta')], default='gravada_10', max_length=15)),
                ('impuesto_porcentaje', models.DecimalField(decimal_places=2, default=10, max_digits=5)),
                ('subtotal', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('impuesto_monto', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=15)),
                ('nota_credito', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lineas', to='ventas.notacredito')),
                ('producto', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lineas_nota_credito', to='productos.producto')),
            ],
            options={
                'verbose_name': 'Línea de Nota de Crédito',
                'verbose_name_plural': 'Líneas de Nota de Crédito',
            },
        ),
    ]
