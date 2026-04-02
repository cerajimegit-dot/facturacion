from django.contrib import admin
from .models import ImportJob


@admin.register(ImportJob)
class ImportJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'empresa', 'tipo', 'estado', 'total_filas', 'filas_importadas', 'created_at']
    list_filter = ['estado', 'tipo', 'empresa']
    search_fields = ['id', 'mensaje']
    readonly_fields = [
        'id', 'reporte_validacion', 'reporte_errores',
        'task_id', 'iniciado_en', 'finalizado_en',
    ]
