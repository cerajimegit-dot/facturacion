"""Serializers para compras y gastos."""
from rest_framework import serializers
from .models import Proveedor, Compra, CompraDetalle, Gasto, CategoriaGasto


class ProveedorSerializer(serializers.ModelSerializer):
    total_compras = serializers.IntegerField(read_only=True)

    class Meta:
        model = Proveedor
        fields = [
            'id', 'nombre', 'ruc_numero', 'pais', 'direccion',
            'telefono', 'email', 'contacto_nombre', 'activo',
            'importancia', 'dias_credito', 'notas',
            'total_compras', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'total_compras']


class ProveedorListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listas."""
    class Meta:
        model = Proveedor
        fields = [
            'id', 'nombre', 'ruc_numero', 'pais', 'email', 'activo'
        ]


class CategoriaGastoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaGasto
        fields = ['id', 'nombre', 'descripcion', 'activo']
        read_only_fields = ['id']


class CompraDetalleSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)
    categoria_nombre = serializers.CharField(source='categoria_gasto.nombre', read_only=True)

    class Meta:
        model = CompraDetalle
        fields = [
            'id', 'compra', 'producto', 'producto_nombre', 'producto_sku',
            'es_servicio', 'categoria_gasto', 'categoria_nombre',
            'descripcion', 'cantidad', 'precio_unitario',
            'impuesto_porcentaje', 'subtotal', 'impuestos', 'total',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'subtotal', 'impuestos', 'total',
            'created_at', 'updated_at'
        ]


class CompraDetailedSerializer(serializers.ModelSerializer):
    """Serializer completo con detalles."""
    detalles = CompraDetalleSerializer(many=True, read_only=True)
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    almacen_nombre = serializers.CharField(source='almacen.nombre', read_only=True)
    usuario_registra_nombre = serializers.CharField(
        source='usuario_registra.get_full_name', read_only=True
    )
    usuario_recepcion_nombre = serializers.CharField(
        source='usuario_recepcion.get_full_name', read_only=True
    )
    puede_recibir = serializers.BooleanField(read_only=True)

    class Meta:
        model = Compra
        fields = [
            'id', 'numero', 'fecha', 'proveedor', 'proveedor_nombre',
            'almacen', 'almacen_nombre', 'moneda', 'cotizacion_usd',
            'detalles', 'subtotal', 'impuestos_total', 'total',
            'estado', 'puede_recibir',
            'usuario_registra', 'usuario_registra_nombre',
            'fecha_recepcion', 'usuario_recepcion', 'usuario_recepcion_nombre',
            'notas', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'subtotal', 'impuestos_total', 'total',
            'puede_recibir', 'fecha_recepcion', 'usuario_recepcion',
            'usuario_recepcion_nombre', 'created_at', 'updated_at'
        ]


class CompraListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listas."""
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True)
    pais_proveedor = serializers.CharField(source='proveedor.pais', read_only=True)

    class Meta:
        model = Compra
        fields = [
            'id', 'numero', 'fecha', 'proveedor', 'proveedor_nombre',
            'pais_proveedor', 'moneda', 'total', 'estado', 'created_at'
        ]


class CompraSerializer(serializers.ModelSerializer):
    """Serializer para crear y actualizar compras."""
    class Meta:
        model = Compra
        fields = [
            'id', 'numero', 'fecha', 'proveedor', 'almacen',
            'moneda', 'cotizacion_usd', 'notas',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate(self, data):
        """Validar que USD tenga cotización."""
        if data.get('moneda') == 'USD' and not data.get('cotizacion_usd'):
            raise serializers.ValidationError(
                "La cotización USD es obligatoria cuando la moneda es USD"
            )
        return data


class GastoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source='categoria.nombre', read_only=True)
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)

    class Meta:
        model = Gasto
        fields = [
            'id', 'fecha', 'categoria', 'categoria_nombre',
            'descripcion', 'monto', 'moneda', 'comprobante',
            'usuario', 'usuario_nombre', 'aprobado', 'notas',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'usuario', 'usuario_nombre', 'created_at', 'updated_at'
        ]
