"""Serializers for Inventario models."""
from rest_framework import serializers
from .models import Almacen, Stock, MovimientoStock


class AlmacenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Almacen
        fields = ['id', 'codigo', 'nombre', 'direccion', 'activo', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class StockSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    almacen_nombre = serializers.CharField(source='almacen.nombre', read_only=True)
    cantidad_disponible = serializers.DecimalField(
        max_digits=15, decimal_places=2, read_only=True
    )

    class Meta:
        model = Stock
        fields = [
            'id', 'producto', 'producto_nombre', 'producto_sku',
            'almacen', 'almacen_nombre',
            'cantidad', 'cantidad_reservada', 'cantidad_disponible',
            'ubicacion', 'stock_minimo',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MovimientoStockSerializer(serializers.ModelSerializer):
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    almacen_codigo = serializers.CharField(source='almacen.codigo', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)

    class Meta:
        model = MovimientoStock
        fields = [
            'id', 'producto', 'producto_sku',
            'almacen', 'almacen_codigo',
            'tipo', 'cantidad', 'referencia', 'nota',
            'usuario', 'usuario_nombre',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'usuario']
