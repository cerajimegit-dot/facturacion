from django.contrib import admin
from .models import Pago


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ['venta', 'cliente', 'empresa', 'fecha', 'monto', 'metodo', 'estado']
    list_filter = ['empresa', 'estado', 'metodo']
    search_fields = ['venta__numero', 'cliente__nombre', 'referencia']
