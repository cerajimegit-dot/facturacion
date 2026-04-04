from django.contrib import admin
from .models import Cotizacion, LineaCotizacion, Venta, LineaVenta, CuentaPorCobrar, RegistroPago


class LineaCotizacionInline(admin.TabularInline):
    model = LineaCotizacion
    extra = 0


class LineaVentaInline(admin.TabularInline):
    model = LineaVenta
    extra = 0


class RegistroPagoInline(admin.TabularInline):
    model = RegistroPago
    extra = 0
    readonly_fields = ['fecha_pago']
    fields = ['monto', 'fecha_pago', 'metodo_pago', 'referencia', 'observaciones']


@admin.register(Cotizacion)
class CotizacionAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'empresa', 'fecha', 'estado', 'total']
    list_filter = ['empresa', 'estado']
    search_fields = ['numero', 'cliente__nombre']
    inlines = [LineaCotizacionInline]


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'empresa', 'fecha', 'estado', 'total', 'saldo_pendiente']
    list_filter = ['empresa', 'estado', 'moneda']
    search_fields = ['numero', 'cliente__nombre', 'cliente__ruc']
    inlines = [LineaVentaInline, RegistroPagoInline]
    fieldsets = (
        ('Información General', {
            'fields': ('numero', 'cliente', 'fecha', 'fecha_vencimiento', 'estado', 'vendedor')
        }),
        ('Montos', {
            'fields': ('total', 'total_pagado', 'saldo_pendiente', 'subtotal', 'impuestos', 'descuento')
        }),
        ('Observaciones', {
            'fields': ('observaciones_cobro', 'notas')
        }),
        ('Información Adicional', {
            'fields': ('moneda', 'tipo_cambio', 'metodo_pago', 'timbrado', 'cdc'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CuentaPorCobrar)
class CuentaPorCobrarAdmin(admin.ModelAdmin):
    list_display = ['venta', 'cliente', 'empresa', 'monto_original', 'saldo', 'estado', 'fecha_vencimiento']
    list_filter = ['empresa', 'estado']
    search_fields = ['venta__numero', 'cliente__nombre']


@admin.register(RegistroPago)
class RegistroPagoAdmin(admin.ModelAdmin):
    list_display = ['venta', 'monto', 'fecha_pago', 'metodo_pago', 'empresa']
    list_filter = ['empresa', 'metodo_pago', 'fecha_pago']
    search_fields = ['venta__numero', 'referencia']
    readonly_fields = ['fecha_pago']
