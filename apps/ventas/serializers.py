"""Serializers for Ventas models."""
from rest_framework import serializers
from .models import (
    Cotizacion, LineaCotizacion, Venta, LineaVenta,
    CuentaPorCobrar, RegistroPago, NotaCredito, LineaNotaCredito,
    CONDICION_IVA_CHOICES,
)


class LineaCotizacionSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = LineaCotizacion
        fields = [
            'id', 'producto', 'producto_nombre', 'descripcion',
            'cantidad', 'precio_unitario', 'descuento_porcentaje',
            'condicion_iva', 'impuesto_porcentaje', 'subtotal', 'impuesto_monto', 'total',
        ]
        read_only_fields = ['id', 'subtotal', 'impuesto_monto', 'total', 'impuesto_porcentaje']


class CotizacionSerializer(serializers.ModelSerializer):
    lineas = LineaCotizacionSerializer(many=True, read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)

    class Meta:
        model = Cotizacion
        fields = [
            'id', 'numero', 'cliente', 'cliente_nombre', 'fecha',
            'fecha_vencimiento', 'estado', 'moneda',
            'subtotal', 'impuestos', 'total', 'notas', 'vendedor',
            'lineas', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'subtotal', 'impuestos', 'total', 'created_at', 'updated_at']


class LineaVentaSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    producto_sku = serializers.CharField(source='producto.sku', read_only=True)

    class Meta:
        model = LineaVenta
        fields = [
            'id', 'producto', 'producto_nombre', 'producto_sku',
            'descripcion', 'cantidad', 'precio_unitario',
            'descuento_porcentaje', 'condicion_iva', 'impuesto_porcentaje',
            'subtotal', 'impuesto_monto', 'total',
        ]
        read_only_fields = ['id', 'subtotal', 'impuesto_monto', 'total', 'impuesto_porcentaje']


class VentaSerializer(serializers.ModelSerializer):
    lineas = LineaVentaSerializer(many=True, read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)

    class Meta:
        model = Venta
        fields = [
            'id', 'numero', 'tipo_comprobante', 'cliente', 'cliente_nombre',
            'cotizacion', 'fecha', 'fecha_vencimiento',
            'estado', 'moneda', 'tipo_cambio',
            'subtotal', 'impuestos', 'descuento', 'total',
            'total_pagado', 'saldo_pendiente',
            'metodo_pago', 'notas', 'observaciones_cobro', 'vendedor',
            'timbrado', 'cdc',
            'lineas', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'subtotal', 'impuestos', 'total',
            'total_pagado', 'saldo_pendiente',
            'created_at', 'updated_at',
        ]


class VentaListSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)

    class Meta:
        model = Venta
        fields = [
            'id', 'numero', 'cliente_nombre', 'fecha',
            'estado', 'total', 'saldo_pendiente', 'moneda',
        ]


class CuentaPorCobrarSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    venta_numero = serializers.CharField(source='venta.numero', read_only=True)

    class Meta:
        model = CuentaPorCobrar
        fields = [
            'id', 'venta', 'venta_numero',
            'cliente', 'cliente_nombre',
            'monto_original', 'monto_pagado', 'saldo', 'moneda',
            'fecha_emision', 'fecha_vencimiento', 'estado', 'notas',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class RegistroPagoSerializer(serializers.ModelSerializer):
    venta_numero = serializers.CharField(source='venta.numero', read_only=True)
    
    class Meta:
        model = RegistroPago
        fields = [
            'id', 'venta', 'venta_numero', 'monto',
            'fecha_pago', 'metodo_pago', 'referencia', 'observaciones'
        ]
        read_only_fields = ['id', 'fecha_pago']


class RegistroPagoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RegistroPago
        fields = ['venta', 'monto', 'metodo_pago', 'referencia', 'observaciones']


class LineaNotaCreditoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)

    class Meta:
        model = LineaNotaCredito
        fields = [
            'id', 'producto', 'producto_nombre', 'descripcion',
            'cantidad', 'precio_unitario', 'condicion_iva',
            'impuesto_porcentaje', 'subtotal', 'impuesto_monto', 'total',
        ]
        read_only_fields = ['id', 'subtotal', 'impuesto_monto', 'total', 'impuesto_porcentaje']


class NotaCreditoSerializer(serializers.ModelSerializer):
    lineas = LineaNotaCreditoSerializer(many=True, read_only=True)
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    venta_numero = serializers.CharField(source='venta_original.numero', read_only=True)

    class Meta:
        model = NotaCredito
        fields = [
            'id', 'numero', 'venta_original', 'venta_numero',
            'cliente', 'cliente_nombre', 'fecha', 'motivo', 'descripcion',
            'subtotal', 'impuestos', 'total', 'estado',
            'lineas', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'subtotal', 'impuestos', 'total', 'created_at', 'updated_at']


class NotaCreditoListSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    venta_numero = serializers.CharField(source='venta_original.numero', read_only=True)

    class Meta:
        model = NotaCredito
        fields = [
            'id', 'numero', 'venta_numero', 'cliente_nombre',
            'fecha', 'motivo', 'total', 'estado',
        ]
