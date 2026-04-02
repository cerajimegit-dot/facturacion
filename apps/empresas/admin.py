from django.contrib import admin
from .models import Empresa


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'ruc', 'moneda_principal', 'activa', 'created_at']
    list_filter = ['activa', 'moneda_principal']
    search_fields = ['codigo', 'nombre', 'ruc']
