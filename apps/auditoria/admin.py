from django.contrib import admin
from .models import Auditoria


@admin.register(Auditoria)
class AuditoriaAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'usuario', 'empresa', 'accion', 'modelo', 'objeto_id']
    list_filter = ['accion', 'modelo', 'empresa']
    search_fields = ['descripcion', 'modelo', 'objeto_id']
    readonly_fields = [
        'id', 'usuario', 'empresa', 'accion', 'modelo', 'objeto_id',
        'datos_anteriores', 'datos_nuevos', 'ip_address', 'user_agent',
        'timestamp', 'descripcion',
    ]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
