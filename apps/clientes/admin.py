from django.contrib import admin
from .models import Cliente, DireccionCliente, ContactoCliente


class DireccionInline(admin.TabularInline):
    model = DireccionCliente
    extra = 0


class ContactoInline(admin.TabularInline):
    model = ContactoCliente
    extra = 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'ruc', 'empresa', 'tipo_cliente', 'activo']
    list_filter = ['empresa', 'tipo_cliente', 'activo']
    search_fields = ['nombre', 'ruc', 'email']
    inlines = [DireccionInline, ContactoInline]
