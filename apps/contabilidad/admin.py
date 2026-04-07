"""Configuración de admin para el módulo de contabilidad."""
from django.contrib import admin
from django.utils.html import format_html

from apps.contabilidad.models import (
    PlanCuentas, Asiento, LineaAsiento, CotizacionDiaria, SaldoCuenta
)


@admin.register(PlanCuentas)
class PlanCuentasAdmin(admin.ModelAdmin):
    """Admin para plan de cuentas."""
    
    list_display = ['codigo_cuenta', 'descripcion_corta', 'condicion_badge', 'clase', 'activa']
    list_filter = ['condicion', 'clase', 'activa', 'empresa']
    search_fields = ['codigo_cuenta', 'descripcion']
    readonly_fields = ['id', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Identificación', {
            'fields': ('id', 'codigo_cuenta', 'codigo_reducido', 'descripcion')
        }),
        ('Característica', {
            'fields': ('condicion', 'clase', 'parent', 'activa')
        }),
        ('Capacidades', {
            'fields': ('acepta_item', 'acepta_centro_costo', 'acepta_nivel')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def descripcion_corta(self, obj):
        return obj.descripcion[:50]
    descripcion_corta.short_description = 'Descripción'
    
    def condicion_badge(self, obj):
        color = '#28a745' if obj.condicion == 'deudora' else '#dc3545'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_condicion_display()
        )
    condicion_badge.short_description = 'Condición'


class LineaAsientoInline(admin.TabularInline):
    """Inline para líneas de asiento."""
    
    model = LineaAsiento
    extra = 1
    fields = ['cuenta', 'debe', 'haber', 'observacion', 'item_contable']
    readonly_fields = ['id']


@admin.register(Asiento)
class AsientoAdmin(admin.ModelAdmin):
    """Admin para asientos contables."""
    
    list_display = ['numero_asiento', 'fecha', 'tipo_asiento', 'total_debe_format', 'estado_badge', 'compra_link']
    list_filter = ['tipo_asiento', 'estado', 'fecha', 'moneda']
    search_fields = ['numero_asiento', 'descripcion', 'compra__numero']
    readonly_fields = ['id', 'numero_asiento', 'total_debe', 'total_haber', 'created_at', 'updated_at']
    inlines = [LineaAsientoInline]
    
    fieldsets = (
        ('Identificación', {
            'fields': ('id', 'numero_asiento', 'tipo_asiento', 'fecha')
        }),
        ('Referencias', {
            'fields': ('compra', 'venta', 'descripcion'),
            'classes': ('collapse',)
        }),
        ('Moneda y Montos', {
            'fields': ('moneda', 'total_debe', 'total_haber')
        }),
        ('Estado', {
            'fields': ('estado', 'usuario_crea', 'usuario_registra', 'fecha_registro')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def total_debe_format(self, obj):
        return f"₲{obj.total_debe:,.2f}"
    total_debe_format.short_description = 'Total'
    
    def estado_badge(self, obj):
        colors = {
            'borrador': '#ffc107',
            'registrado': '#28a745',
            'reversado': '#6c757d'
        }
        color = colors.get(obj.estado, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_estado_display()
        )
    estado_badge.short_description = 'Estado'
    
    def compra_link(self, obj):
        if obj.compra:
            return format_html(
                '<a href="/admin/compras/compra/{}/change/">{}</a>',
                obj.compra.id,
                obj.compra.numero
            )
        return '—'
    compra_link.short_description = 'Compra'


@admin.register(LineaAsiento)
class LineaAsientoAdmin(admin.ModelAdmin):
    """Admin para líneas de asiento."""
    
    list_display = ['asiento', 'cuenta', 'debe_format', 'haber_format', 'item_contable']
    list_filter = ['asiento__fecha', 'cuenta__condicion']
    search_fields = ['asiento__numero_asiento', 'cuenta__codigo_cuenta', 'observacion']
    readonly_fields = ['id', 'created_at']
    
    def debe_format(self, obj):
        return f"₲{obj.debe:,.2f}" if obj.debe > 0 else '—'
    debe_format.short_description = 'Debe'
    
    def haber_format(self, obj):
        return f"₲{obj.haber:,.2f}" if obj.haber > 0 else '—'
    haber_format.short_description = 'Haber'


@admin.register(CotizacionDiaria)
class CotizacionDiariaAdmin(admin.ModelAdmin):
    """Admin para cotizaciones diarias."""
    
    list_display = ['fecha', 'conversion', 'tasa_format', 'usuario_carga']
    list_filter = ['fecha', 'moneda_origen', 'moneda_destino']
    search_fields = ['fecha']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'fecha'
    
    def conversion(self, obj):
        return f"{obj.moneda_origen} → {obj.moneda_destino}"
    conversion.short_description = 'Conversión'
    
    def tasa_format(self, obj):
        return f"{obj.tasa:,.6f}"
    tasa_format.short_description = 'Tasa'


@admin.register(SaldoCuenta)
class SaldoCuentaAdmin(admin.ModelAdmin):
    """Admin para saldos de cuenta."""
    
    list_display = ['cuenta', 'fecha', 'saldo_anterior_format', 'movimiento_neto_format', 'saldo_actual_format']
    list_filter = ['fecha', 'cuenta__condicion']
    search_fields = ['cuenta__codigo_cuenta', 'cuenta__descripcion']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'fecha'
    
    def saldo_anterior_format(self, obj):
        return f"₲{obj.saldo_anterior:,.2f}"
    saldo_anterior_format.short_description = 'Saldo Anterior'
    
    def movimiento_neto_format(self, obj):
        neto = obj.movimiento_debe - obj.movimiento_haber
        color = '#28a745' if neto >= 0 else '#dc3545'
        return format_html(
            '<span style="color: {};">₲{:,.2f}</span>',
            color, neto
        )
    movimiento_neto_format.short_description = 'Movimiento Neto'
    
    def saldo_actual_format(self, obj):
        return f"₲{obj.saldo_actual:,.2f}"
    saldo_actual_format.short_description = 'Saldo Actual'
