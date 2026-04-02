from django.contrib import admin
from .models import Categoria, Producto, Variante, PrecioLista


class VarianteInline(admin.TabularInline):
    model = Variante
    extra = 0


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'empresa', 'padre']
    list_filter = ['empresa']
    search_fields = ['nombre']


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ['sku', 'nombre', 'empresa', 'tipo', 'precio_unitario', 'activo']
    list_filter = ['empresa', 'tipo', 'activo', 'categoria']
    search_fields = ['sku', 'nombre']
    inlines = [VarianteInline]


@admin.register(PrecioLista)
class PrecioListaAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'producto', 'precio', 'moneda', 'empresa']
    list_filter = ['empresa', 'moneda']
