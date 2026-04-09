"""Serializers para el módulo de Activos Fijos."""
from rest_framework import serializers
from .models import (
    ClasificacionActivo, UbicacionActivo, CentroCosto,
    ActivoFijo, MovimientoActivo, MantenimientoActivo,
    BajaActivo, DepreciacionMensual,
)


class ClasificacionActivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClasificacionActivo
        fields = ['id', 'nombre', 'descripcion', 'vida_util_default', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class UbicacionActivoSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = UbicacionActivo
        fields = ['id', 'planta', 'edificio', 'area', 'nombre_completo', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_nombre_completo(self, obj):
        return str(obj)


class CentroCostoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CentroCosto
        fields = ['id', 'codigo', 'descripcion', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ActivoFijoSerializer(serializers.ModelSerializer):
    clasificacion_nombre = serializers.CharField(source='clasificacion.nombre', read_only=True, allow_null=True)
    ubicacion_nombre = serializers.SerializerMethodField()
    centro_costo_nombre = serializers.CharField(source='centro_costo.descripcion', read_only=True, allow_null=True)
    responsable_nombre = serializers.SerializerMethodField()
    proveedor_nombre = serializers.CharField(source='proveedor.nombre', read_only=True, allow_null=True)
    depreciacion_mensual = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    depreciacion_anual = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    porcentaje_depreciado = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    vida_util_restante_meses = serializers.IntegerField(read_only=True)
    esta_totalmente_depreciado = serializers.BooleanField(read_only=True)
    supera_vida_util = serializers.BooleanField(read_only=True)

    class Meta:
        model = ActivoFijo
        fields = [
            'id', 'codigo', 'nombre', 'descripcion', 'tipo',
            'clasificacion', 'clasificacion_nombre',
            'ubicacion', 'ubicacion_nombre',
            'centro_costo', 'centro_costo_nombre',
            'valor_adquisicion', 'valor_residual',
            'fecha_adquisicion', 'fecha_activacion',
            'vida_util_anios', 'estado',
            'proveedor', 'proveedor_nombre',
            'responsable', 'responsable_nombre',
            'numero_serie', 'numero_factura', 'imagen', 'notas',
            'depreciacion_acumulada', 'valor_libro',
            'depreciacion_mensual', 'depreciacion_anual',
            'porcentaje_depreciado', 'vida_util_restante_meses',
            'esta_totalmente_depreciado', 'supera_vida_util',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'depreciacion_acumulada', 'valor_libro',
            'created_at', 'updated_at',
        ]

    def get_ubicacion_nombre(self, obj):
        return str(obj.ubicacion) if obj.ubicacion else None

    def get_responsable_nombre(self, obj):
        if obj.responsable:
            return obj.responsable.get_full_name() or obj.responsable.email
        return None


class ActivoFijoListSerializer(serializers.ModelSerializer):
    clasificacion_nombre = serializers.CharField(source='clasificacion.nombre', read_only=True, allow_null=True)
    ubicacion_nombre = serializers.SerializerMethodField()
    responsable_nombre = serializers.SerializerMethodField()

    class Meta:
        model = ActivoFijo
        fields = [
            'id', 'codigo', 'nombre', 'tipo',
            'clasificacion_nombre', 'ubicacion_nombre',
            'valor_adquisicion', 'valor_libro', 'estado',
            'responsable_nombre', 'fecha_adquisicion',
        ]

    def get_ubicacion_nombre(self, obj):
        return str(obj.ubicacion) if obj.ubicacion else None

    def get_responsable_nombre(self, obj):
        if obj.responsable:
            return obj.responsable.get_full_name() or obj.responsable.email
        return None


class MovimientoActivoSerializer(serializers.ModelSerializer):
    activo_codigo = serializers.CharField(source='activo.codigo', read_only=True)
    activo_nombre = serializers.CharField(source='activo.nombre', read_only=True)
    ubicacion_origen_nombre = serializers.SerializerMethodField()
    ubicacion_destino_nombre = serializers.SerializerMethodField()

    class Meta:
        model = MovimientoActivo
        fields = [
            'id', 'activo', 'activo_codigo', 'activo_nombre',
            'fecha', 'ubicacion_origen', 'ubicacion_origen_nombre',
            'ubicacion_destino', 'ubicacion_destino_nombre',
            'responsable_anterior', 'responsable_nuevo',
            'motivo', 'usuario_registro', 'created_at',
        ]
        read_only_fields = ['id', 'usuario_registro', 'created_at']

    def get_ubicacion_origen_nombre(self, obj):
        return str(obj.ubicacion_origen) if obj.ubicacion_origen else None

    def get_ubicacion_destino_nombre(self, obj):
        return str(obj.ubicacion_destino) if obj.ubicacion_destino else None


class MantenimientoActivoSerializer(serializers.ModelSerializer):
    activo_codigo = serializers.CharField(source='activo.codigo', read_only=True)
    activo_nombre = serializers.CharField(source='activo.nombre', read_only=True)
    usuario_nombre = serializers.SerializerMethodField()

    class Meta:
        model = MantenimientoActivo
        fields = [
            'id', 'activo', 'activo_codigo', 'activo_nombre',
            'fecha', 'fecha_fin', 'tipo', 'estado',
            'descripcion', 'costo', 'proveedor_servicio',
            'usuario', 'usuario_nombre', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_usuario_nombre(self, obj):
        if obj.usuario:
            return obj.usuario.get_full_name() or obj.usuario.email
        return None


class BajaActivoSerializer(serializers.ModelSerializer):
    activo_codigo = serializers.CharField(source='activo.codigo', read_only=True)
    activo_nombre = serializers.CharField(source='activo.nombre', read_only=True)

    class Meta:
        model = BajaActivo
        fields = [
            'id', 'activo', 'activo_codigo', 'activo_nombre',
            'fecha_baja', 'motivo', 'motivo_detalle',
            'valor_rescate', 'usuario', 'autorizado_por',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'usuario', 'created_at', 'updated_at']


class DepreciacionMensualSerializer(serializers.ModelSerializer):
    activo_codigo = serializers.CharField(source='activo.codigo', read_only=True)

    class Meta:
        model = DepreciacionMensual
        fields = [
            'id', 'activo', 'activo_codigo',
            'anio', 'mes', 'monto',
            'depreciacion_acumulada', 'valor_libro',
        ]
        read_only_fields = ['id']
