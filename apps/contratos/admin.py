from django.contrib import admin
from .models import Contrato, OrdenServicio


@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'empresa', 'estado', 'monto_recurrente', 'fecha_inicio']
    list_filter = ['empresa', 'estado', 'frecuencia_cobro']
    search_fields = ['numero', 'cliente__nombre']


@admin.register(OrdenServicio)
class OrdenServicioAdmin(admin.ModelAdmin):
    list_display = ['numero', 'cliente', 'empresa', 'estado', 'prioridad', 'fecha_programada']
    list_filter = ['empresa', 'estado', 'prioridad']
    search_fields = ['numero', 'cliente__nombre', 'descripcion']
