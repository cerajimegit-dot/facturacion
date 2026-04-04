"""Admin interface para módulo de compras."""
from django.contrib import admin
from .models import Proveedor, CategoriaGasto, Compra, CompraDetalle, Gasto


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ruc_numero', 'pais', 'email', 'empresa', 'activo']
    list_filter = ['empresa', 'pais', 'activo']
    search_fields = ['nombre', 'ruc_numero', 'email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información General', {
            'fields': ('empresa', 'nombre', 'ruc_numero', 'pais')
        }),
        ('Contacto', {
            'fields': ('contacto_nombre', 'email', 'telefono')
        }),
        ('Dirección', {
            'fields': ('direccion',)
        }),
        ('Estado', {
            'fields': ('activo',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CategoriaGasto)
class CategoriaGastoAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'activo']
    list_filter = ['activo']
    search_fields = ['nombre']
    
    fieldsets = (
        ('Información', {
            'fields': ('nombre', 'descripcion', 'activo')
        }),
    )


class CompraDetalleInline(admin.TabularInline):
    """Inline para detalles de compra."""
    model = CompraDetalle
    extra = 1
    fields = ['producto', 'es_servicio', 'categoria_gasto', 'cantidad', 
              'precio_unitario', 'impuesto_porcentaje', 'subtotal', 'impuestos', 'total']
    readonly_fields = ['subtotal', 'impuestos', 'total']


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ['numero', 'proveedor', 'fecha', 'empresa', 'estado', 'total', 'moneda']
    list_filter = ['empresa', 'estado', 'moneda', 'fecha']
    search_fields = ['numero', 'proveedor__nombre']
    readonly_fields = ['created_at', 'updated_at', 'usuario_registra', 
                       'usuario_recepcion', 'fecha_recepcion', 'subtotal', 'impuestos_total', 'total']
    inlines = [CompraDetalleInline]
    
    fieldsets = (
        ('Información General', {
            'fields': ('empresa', 'numero', 'fecha', 'proveedor', 'almacen')
        }),
        ('Moneda y Cotización', {
            'fields': ('moneda', 'cotizacion_usd')
        }),
        ('Totales', {
            'fields': ('subtotal', 'impuestos_total', 'total'),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': ('estado', 'fecha_recepcion')
        }),
        ('Auditoría', {
            'fields': ('usuario_registra', 'usuario_recepcion', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CompraDetalle)
class CompraDetalleAdmin(admin.ModelAdmin):
    list_display = ['compra', 'producto', 'es_servicio', 'categoria_gasto', 
                    'cantidad', 'precio_unitario', 'total']
    list_filter = ['compra__empresa', 'es_servicio', 'compra__fecha']
    search_fields = ['compra__numero', 'producto__nombre', 'categoria_gasto__nombre']
    readonly_fields = ['subtotal', 'impuestos', 'total']
    
    fieldsets = (
        ('Compra', {
            'fields': ('compra',)
        }),
        ('Producto o Servicio', {
            'fields': ('producto', 'es_servicio', 'categoria_gasto')
        }),
        ('Cantidades y Precios', {
            'fields': ('cantidad', 'precio_unitario', 'impuesto_porcentaje')
        }),
        ('Totales', {
            'fields': ('subtotal', 'impuestos', 'total'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    list_display = ['fecha', 'categoria', 'monto', 'moneda', 'empresa', 'aprobado', 'usuario']
    list_filter = ['empresa', 'categoria', 'aprobado', 'moneda', 'fecha']
    search_fields = ['descripcion', 'comprobante']
    readonly_fields = ['created_at', 'updated_at', 'usuario']
    
    fieldsets = (
        ('Información General', {
            'fields': ('empresa', 'fecha', 'categoria', 'descripcion')
        }),
        ('Montos', {
            'fields': ('monto', 'moneda')
        }),
        ('Documentación', {
            'fields': ('comprobante',)
        }),
        ('Aprobación', {
            'fields': ('aprobado',)
        }),
        ('Auditoría', {
            'fields': ('usuario', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
