from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario, Membership


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ['username', 'email', 'first_name', 'last_name', 'is_active']
    fieldsets = UserAdmin.fieldsets + (
        ('Extra', {'fields': ('telefono', 'avatar', 'idioma', 'zona_horaria')}),
    )


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ['usuario', 'empresa', 'rol', 'activo', 'created_at']
    list_filter = ['rol', 'activo']
    search_fields = ['usuario__username', 'empresa__nombre']
