"""Serializers para el módulo de contabilidad."""
from rest_framework import serializers
from decimal import Decimal

from apps.contabilidad.models import (
    PlanCuentas, Asiento, LineaAsiento, CotizacionDiaria, SaldoCuenta
)


class PlanCuentasSerializer(serializers.ModelSerializer):
    """Serializer para plan de cuentas."""
    
    class Meta:
        model = PlanCuentas
        fields = [
            'id', 'codigo_cuenta', 'codigo_reducido', 'descripcion',
            'condicion', 'clase', 'acepta_item', 'acepta_centro_costo',
            'acepta_nivel', 'activa', 'parent', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PlanCuentasListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listas."""
    
    class Meta:
        model = PlanCuentas
        fields = [
            'id', 'codigo_cuenta', 'descripcion', 'condicion',
            'clase', 'activa'
        ]


class LineaAsientoSerializer(serializers.ModelSerializer):
    """Serializer para línea de asiento."""
    
    cuenta_codigo = serializers.CharField(source='cuenta.codigo_cuenta', read_only=True)
    cuenta_descripcion = serializers.CharField(source='cuenta.descripcion', read_only=True)
    compra_detalle_descripcion = serializers.CharField(
        source='compra_detalle.descripcion',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = LineaAsiento
        fields = [
            'id', 'asiento', 'cuenta', 'cuenta_codigo', 'cuenta_descripcion',
            'debe', 'haber', 'observacion', 'item_contable',
            'centro_costo', 'nivel', 'compra_detalle', 'compra_detalle_descripcion',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AsientoDetailedSerializer(serializers.ModelSerializer):
    """Serializer detallado de asiento con líneas."""
    
    lineas = LineaAsientoSerializer(many=True, read_only=True)
    compra_numero = serializers.CharField(source='compra.numero', read_only=True, allow_null=True)
    proveedor_nombre = serializers.CharField(
        source='compra.proveedor.nombre',
        read_only=True,
        allow_null=True
    )
    usuario_crea_nombre = serializers.CharField(
        source='usuario_crea.get_full_name',
        read_only=True,
        allow_null=True
    )
    usuario_registra_nombre = serializers.CharField(
        source='usuario_registra.get_full_name',
        read_only=True,
        allow_null=True
    )
    
    venta_numero = serializers.CharField(source='venta.numero', read_only=True, allow_null=True)
    cliente_nombre = serializers.CharField(
        source='venta.cliente.nombre',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = Asiento
        fields = [
            'id', 'numero_asiento', 'tipo_asiento', 'fecha', 'descripcion',
            'compra', 'compra_numero', 'proveedor_nombre',
            'venta', 'venta_numero', 'cliente_nombre',
            'moneda', 'total_debe', 'total_haber', 'estado',
            'usuario_crea', 'usuario_crea_nombre',
            'usuario_registra', 'usuario_registra_nombre',
            'fecha_registro', 'lineas', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'numero_asiento', 'total_debe', 'total_haber',
            'created_at', 'updated_at'
        ]


class AsientoListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listas de asientos."""
    
    compra_numero = serializers.CharField(source='compra.numero', read_only=True, allow_null=True)
    venta_numero = serializers.CharField(source='venta.numero', read_only=True, allow_null=True)
    
    class Meta:
        model = Asiento
        fields = [
            'id', 'numero_asiento', 'tipo_asiento', 'fecha',
            'compra_numero', 'venta_numero', 'moneda', 'total_debe', 'total_haber',
            'estado', 'created_at'
        ]


class AsientoCrearSerializer(serializers.ModelSerializer):
    """Serializer para crear asientosx."""
    
    lineas_data = serializers.ListField(
        child=serializers.DictField(),
        write_only=True,
        required=True
    )
    
    class Meta:
        model = Asiento
        fields = [
            'numero_asiento', 'tipo_asiento', 'fecha', 'descripcion',
            'moneda', 'lineas_data'
        ]
    
    def validate_lineas_data(self, value):
        """Validar líneas de asiento."""
        if not value or len(value) == 0:
            raise serializers.ValidationError("Debe agregar al menos una línea")
        
        total_debe = Decimal('0')
        total_haber = Decimal('0')
        
        for idx, linea in enumerate(value):
            if not linea.get('cuenta'):
                raise serializers.ValidationError(f"Línea {idx+1}: Falta cuenta")
            
            debe = Decimal(str(linea.get('debe', 0)))
            haber = Decimal(str(linea.get('haber', 0)))
            
            if debe > 0 and haber > 0:
                raise serializers.ValidationError(
                    f"Línea {idx+1}: No puede tener debe y haber simultáneamente"
                )
            if debe == 0 and haber == 0:
                raise serializers.ValidationError(f"Línea {idx+1}: Debe tener debe o haber")
            
            total_debe += debe
            total_haber += haber
        
        if total_debe != total_haber:
            raise serializers.ValidationError(
                f"Asiento desbalanceado: Debe={total_debe}, Haber={total_haber}"
            )
        
        return value
    
    def create(self, validated_data):
        """Crear asiento con líneas."""
        lineas_data = validated_data.pop('lineas_data', [])
        
        asiento = Asiento.objects.create(**validated_data)
        
        total_debe = Decimal('0')
        total_haber = Decimal('0')
        
        for linea_data in lineas_data:
            cuenta = linea_data.pop('cuenta')
            debe = Decimal(str(linea_data.get('debe', 0)))
            haber = Decimal(str(linea_data.get('haber', 0)))
            
            LineaAsiento.objects.create(
                asiento=asiento,
                empresa=asiento.empresa,
                cuenta_id=cuenta,
                debe=debe,
                haber=haber,
                **linea_data
            )
            
            total_debe += debe
            total_haber += haber
        
        asiento.total_debe = total_debe
        asiento.total_haber = total_haber
        asiento.save()
        
        return asiento


class CotizacionDiariaSerializer(serializers.ModelSerializer):
    """Serializer para cotización diaria."""
    
    usuario_carga_nombre = serializers.CharField(
        source='usuario_carga.get_full_name',
        read_only=True,
        allow_null=True
    )
    
    class Meta:
        model = CotizacionDiaria
        fields = [
            'id', 'fecha', 'moneda_origen', 'moneda_destino', 'tasa',
            'usuario_carga', 'usuario_carga_nombre', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class SaldoCuentaSerializer(serializers.ModelSerializer):
    """Serializer para saldo de cuenta."""
    
    cuenta_codigo = serializers.CharField(source='cuenta.codigo_cuenta', read_only=True)
    cuenta_descripcion = serializers.CharField(source='cuenta.descripcion', read_only=True)
    
    class Meta:
        model = SaldoCuenta
        fields = [
            'id', 'cuenta', 'cuenta_codigo', 'cuenta_descripcion', 'fecha',
            'saldo_anterior', 'movimiento_debe', 'movimiento_haber',
            'saldo_actual', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class BalanceGeneralSerializer(serializers.Serializer):
    """Serializer para balance general."""
    
    fecha = serializers.DateField()
    activos = serializers.DecimalField(max_digits=18, decimal_places=2)
    pasivos = serializers.DecimalField(max_digits=18, decimal_places=2)
    patrimonio = serializers.DecimalField(max_digits=18, decimal_places=2)
    
    def to_representation(self, instance):
        """Formato del balance."""
        return {
            'fecha': instance['fecha'],
            'estado': 'Balanceado' if instance['activos'] == instance['pasivos'] + instance['patrimonio'] else 'Desbalanceado',
            'activos': str(instance['activos']),
            'pasivos': str(instance['pasivos']),
            'patrimonio': str(instance['patrimonio']),
        }
