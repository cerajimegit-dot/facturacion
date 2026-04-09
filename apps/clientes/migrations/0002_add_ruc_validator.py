# Migration: Add RUC validator to Cliente
from django.db import migrations, models
import apps.clientes.models


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cliente',
            name='ruc',
            field=models.CharField(
                blank=True,
                default='',
                max_length=30,
                validators=[apps.clientes.models.validar_ruc_paraguayo],
            ),
        ),
    ]
