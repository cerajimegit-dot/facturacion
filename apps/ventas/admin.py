from django.contrib import admin
from .models import Cotizacion, LineaCotizacion, Venta, LineaVenta, CuentaPorCobrar


class LineaCotizacionInline(admin.TabularInline):
    model = LineaCotizacion
    extra = 0


class LineaVentaInline(admin.TabularInline):
    model = LineaVenta
    extra = 0


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
    inlines = [LineaVentaInline]


@admin.register(CuentaPorCobrar)
class CuentaPorCobrarAdmin(admin.ModelAdmin):
    list_display = ['venta', 'cliente', 'empresa', 'monto_original', 'saldo', 'estado', 'fecha_vencimiento']
    list_filter = ['empresa', 'estado']
    search_fields = ['venta__numero', 'cliente__nombre']
