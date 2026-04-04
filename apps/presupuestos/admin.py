"""Django admin for presupuestos."""
from django.contrib import admin
from .models import Presupuesto, PresupuestoDetalle


class PresupuestoDetalleInline(admin.TabularInline):
    """Inline admin for presupuesto details."""
    model = PresupuestoDetalle
    extra = 0
    fields = ['producto', 'descripcion', 'cantidad', 'precio_unitario', 'impuesto_porcentaje', 'total']
    readonly_fields = ['total']


@admin.register(Presupuesto)
class PresupuestoAdmin(admin.ModelAdmin):
    """Admin for Presupuesto."""
    list_display = ['numero', 'cliente', 'estado', 'total', 'fecha_creacion']
    list_filter = ['estado', 'fecha_creacion', 'empresa']
    search_fields = ['numero', 'cliente__nombre']
    readonly_fields = ['numero', 'subtotal', 'total_impuesto', 'total', 'fecha_creacion', 'actualizado_en']
    fieldsets = (
        ('Información General', {
            'fields': ('numero', 'cliente', 'estado', 'empresa')
        }),
        ('Detalle Económico', {
            'fields': ('subtotal', 'total_impuesto', 'total', 'moneda')
        }),
        ('Contacto', {
            'fields': ('email_cliente', 'telefono_cliente')
        }),
        ('Fechas', {
            'fields': ('fecha_creacion', 'fecha_vigencia', 'fecha_envio', 'actualizado_en')
        }),
        ('Información Adicional', {
            'fields': ('descripcion', 'notas', 'condiciones_pago', 'creado_por'),
            'classes': ('collapse',)
        }),
    )
    inlines = [PresupuestoDetalleInline]
    
    def save_model(self, request, obj, form, change):
        """Auto-generate numero on create."""
        if not obj.numero:
            obj.generar_numero()
        if not obj.creado_por_id:
            obj.creado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(PresupuestoDetalle)
class PresupuestoDetalleAdmin(admin.ModelAdmin):
    """Admin for PresupuestoDetalle."""
    list_display = ['presupuesto', 'descripcion', 'cantidad', 'precio_unitario', 'total']
    list_filter = ['presupuesto__estado', 'presupuesto__fecha_creacion']
    search_fields = ['presupuesto__numero', 'descripcion']
    readonly_fields = ['total', 'subtotal', 'total_impuesto']
    
    def save_model(self, request, obj, form, change):
        """Auto-calculate totals."""
        super().save_model(request, obj, form, change)
        obj.calcular_totales()
