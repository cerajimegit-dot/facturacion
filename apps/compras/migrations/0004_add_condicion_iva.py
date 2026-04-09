# Migration: Add condicion_iva to CompraDetalle
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0003_proveedor_cuenta_contable_proveedor_email_set_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='compradetalle',
            name='condicion_iva',
            field=models.CharField(
                choices=[('gravada_10', 'Gravada 10%'), ('gravada_5', 'Gravada 5%'), ('exenta', 'Exenta')],
                default='gravada_10',
                help_text='Condición de IVA según Ley 6380/19',
                max_length=15,
            ),
        ),
    ]
