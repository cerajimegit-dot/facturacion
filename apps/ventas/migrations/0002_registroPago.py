# Generated migration for ventas app

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0001_initial'),  # Adjust if needed
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='observaciones_cobro',
            field=models.TextField(blank=True, default='', help_text='Observaciones sobre pagos y avance de cobro'),
        ),
        migrations.CreateModel(
            name='RegistroPago',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('monto', models.DecimalField(decimal_places=2, max_digits=15)),
                ('fecha_pago', models.DateTimeField(auto_now_add=True)),
                ('metodo_pago', models.CharField(blank=True, default='', max_length=50)),
                ('referencia', models.CharField(blank=True, default='', max_length=100)),
                ('observaciones', models.TextField(blank=True, default='')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='empresas.empresa')),
                ('venta', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='registro_pagos', to='ventas.venta')),
            ],
            options={
                'verbose_name': 'Registro de Pago',
                'verbose_name_plural': 'Registros de Pago',
                'ordering': ['-fecha_pago'],
            },
        ),
    ]
