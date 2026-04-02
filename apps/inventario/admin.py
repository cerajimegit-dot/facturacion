from django.contrib import admin
from .models import Almacen, Stock, MovimientoStock


@admin.register(Almacen)
class AlmacenAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'empresa', 'activo']
    list_filter = ['empresa', 'activo']
    search_fields = ['codigo', 'nombre']


@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['producto', 'almacen', 'empresa', 'cantidad', 'cantidad_reservada', 'stock_minimo']
    list_filter = ['empresa', 'almacen']
    search_fields = ['producto__sku', 'producto__nombre']


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ['producto', 'almacen', 'tipo', 'cantidad', 'usuario', 'created_at']
    list_filter = ['empresa', 'tipo', 'almacen']
    search_fields = ['producto__sku', 'referencia']
