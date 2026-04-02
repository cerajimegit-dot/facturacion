"""Serializers for Pago model."""
from rest_framework import serializers
from .models import Pago


class PagoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    venta_numero = serializers.CharField(source='venta.numero', read_only=True)
    cliente = serializers.PrimaryKeyRelatedField(required=False, queryset=Pago.cliente.field.related_model.objects.all())

    class Meta:
        model = Pago
        fields = [
            'id', 'venta', 'venta_numero',
            'cliente', 'cliente_nombre',
            'fecha', 'monto', 'moneda', 'metodo',
            'referencia', 'estado', 'notas', 'comprobante',
            'registrado_por', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'registrado_por', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Auto-populate cliente from venta if not provided
        if 'cliente' not in validated_data or validated_data['cliente'] is None:
            venta = validated_data.get('venta')
            if venta:
                validated_data['cliente'] = venta.cliente
        # Auto-set registrado_por
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['registrado_por'] = request.user
        return super().create(validated_data)
