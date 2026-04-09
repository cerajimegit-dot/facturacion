from django.contrib import admin
from .models import (
    ClasificacionActivo, UbicacionActivo, CentroCosto,
    ActivoFijo, MovimientoActivo, MantenimientoActivo,
    BajaActivo, DepreciacionMensual,
)


@admin.register(ClasificacionActivo)
class ClasificacionActivoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'vida_util_default', 'empresa']
    list_filter = ['empresa']
    search_fields = ['nombre']


@admin.register(UbicacionActivo)
class UbicacionActivoAdmin(admin.ModelAdmin):
    list_display = ['planta', 'edificio', 'area', 'empresa']
    list_filter = ['empresa']
    search_fields = ['planta', 'edificio', 'area']


@admin.register(CentroCosto)
class CentroCostoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'descripcion', 'empresa']
    list_filter = ['empresa']
    search_fields = ['codigo', 'descripcion']


@admin.register(ActivoFijo)
class ActivoFijoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'tipo', 'estado', 'valor_adquisicion', 'valor_libro', 'empresa']
    list_filter = ['empresa', 'tipo', 'estado']
    search_fields = ['codigo', 'nombre', 'numero_serie']
    readonly_fields = ['depreciacion_acumulada', 'valor_libro']


@admin.register(MovimientoActivo)
class MovimientoActivoAdmin(admin.ModelAdmin):
    list_display = ['activo', 'fecha', 'ubicacion_origen', 'ubicacion_destino']
    list_filter = ['empresa']


@admin.register(MantenimientoActivo)
class MantenimientoActivoAdmin(admin.ModelAdmin):
    list_display = ['activo', 'fecha', 'tipo', 'estado', 'costo']
    list_filter = ['empresa', 'tipo', 'estado']


@admin.register(BajaActivo)
class BajaActivoAdmin(admin.ModelAdmin):
    list_display = ['activo', 'fecha_baja', 'motivo', 'valor_rescate']
    list_filter = ['empresa', 'motivo']


@admin.register(DepreciacionMensual)
class DepreciacionMensualAdmin(admin.ModelAdmin):
    list_display = ['activo', 'anio', 'mes', 'monto', 'valor_libro']
    list_filter = ['empresa', 'anio', 'mes']
