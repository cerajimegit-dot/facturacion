"""Serializers for presupuestos app."""
from rest_framework import serializers
from .models import Presupuesto, PresupuestoDetalle
from apps.clientes.serializers import ClienteSerializer
from apps.productos.serializers import ProductoSerializer


class PresupuestoDetalleSerializer(serializers.ModelSerializer):
    producto_data = ProductoSerializer(source='producto', read_only=True)
    
    class Meta:
        model = PresupuestoDetalle
        fields = [
            'id', 'producto', 'producto_data', 'descripcion',
            'cantidad', 'precio_unitario', 'impuesto_porcentaje',
            'subtotal', 'total_impuesto', 'total', 'orden'
        ]


class PresupuestoSerializer(serializers.ModelSerializer):
    cliente_data = ClienteSerializer(source='cliente', read_only=True)
    detalles = PresupuestoDetalleSerializer(many=True, read_only=True)
    
    class Meta:
        model = Presupuesto
        fields = [
            'id', 'numero', 'cliente', 'cliente_data', 'fecha_creacion',
            'fecha_vigencia', 'fecha_envio', 'estado',
            'subtotal', 'total_impuesto', 'total', 'moneda',
            'email_cliente', 'telefono_cliente',
            'descripcion', 'notas', 'condiciones_pago',
            'detalles', 'actualizado_en'
        ]
        read_only_fields = ['numero', 'fecha_creacion', 'actualizado_en', 'subtotal', 'total_impuesto', 'total']


class PresupuestoCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating presupuestos."""
    detalles = PresupuestoDetalleSerializer(many=True, required=False)
    
    class Meta:
        model = Presupuesto
        fields = [
            'cliente', 'fecha_vigencia', 'estado',
            'email_cliente', 'telefono_cliente',
            'descripcion', 'notas', 'condiciones_pago', 'detalles'
        ]
    
    def create(self, validated_data):
        detalles_data = validated_data.pop('detalles', [])
        presupuesto = Presupuesto.objects.create(**validated_data)
        presupuesto.generar_numero()
        presupuesto.save()
        
        for detalle_data in detalles_data:
            detalle = PresupuestoDetalle.objects.create(presupuesto=presupuesto, **detalle_data)
            detalle.calcular_totales()
        
        presupuesto.calcular_totales()
        return presupuesto
    
    def update(self, instance, validated_data):
        detalles_data = validated_data.pop('detalles', [])
        
        # Update presupuesto fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Update detalles if provided
        if detalles_data:
            instance.detalles.all().delete()
            for detalle_data in detalles_data:
                detalle = PresupuestoDetalle.objects.create(presupuesto=instance, **detalle_data)
                detalle.calcular_totales()
            instance.calcular_totales()
        
        return instance
