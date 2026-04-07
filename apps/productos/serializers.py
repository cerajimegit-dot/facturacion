"""Serializers for Producto, Variante, PrecioLista, Categoria."""
from rest_framework import serializers
from .models import Producto, Variante, PrecioLista, Categoria


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'descripcion', 'padre', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class VarianteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Variante
        fields = ['id', 'nombre', 'sku_variante', 'precio_diferencial', 'activo']
        read_only_fields = ['id']


class PrecioListaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrecioLista
        fields = [
            'id', 'nombre', 'producto', 'precio', 'moneda',
            'vigente_desde', 'vigente_hasta', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ProductoSerializer(serializers.ModelSerializer):
    variantes = VarianteSerializer(many=True, read_only=True)
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    cuenta_contable_desc = serializers.CharField(source='cuenta_contable.descripcion', read_only=True, allow_null=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'sku', 'nombre', 'descripcion', 'tipo',
            'categoria', 'categoria_nombre',
            'precio_unitario', 'costo', 'moneda',
            'impuesto_porcentaje', 'imagen_url', 'imagen', 'activo',
            'cuenta_contable', 'cuenta_contable_desc',
            'variantes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'cuenta_contable_desc']


class ProductoUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating productos - makes SKU optional."""
    variantes = VarianteSerializer(many=True, read_only=True)
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    cuenta_contable_desc = serializers.CharField(source='cuenta_contable.descripcion', read_only=True, allow_null=True)

    class Meta:
        model = Producto
        fields = [
            'id', 'sku', 'nombre', 'descripcion', 'tipo',
            'categoria', 'categoria_nombre',
            'precio_unitario', 'costo', 'moneda',
            'impuesto_porcentaje', 'imagen_url', 'imagen', 'activo',
            'cuenta_contable', 'cuenta_contable_desc',
            'variantes', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'sku', 'created_at', 'updated_at', 'cuenta_contable_desc']  # SKU is read-only on updates


class ProductoListSerializer(serializers.ModelSerializer):
    cuenta_contable_desc = serializers.CharField(source='cuenta_contable.descripcion', read_only=True, allow_null=True)
    
    class Meta:
        model = Producto
        fields = [
            'id', 'sku', 'nombre', 'descripcion', 'tipo',
            'categoria', 'precio_unitario', 'costo', 'moneda',
            'impuesto_porcentaje', 'imagen_url', 'activo',
            'cuenta_contable', 'cuenta_contable_desc',
        ]
        read_only_fields = ['cuenta_contable_desc']
