"""Serializers for Cliente, DireccionCliente, ContactoCliente."""
from rest_framework import serializers
from .models import Cliente, DireccionCliente, ContactoCliente


class DireccionClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DireccionCliente
        fields = [
            'id', 'etiqueta', 'direccion', 'ciudad',
            'departamento', 'pais', 'es_principal',
        ]
        read_only_fields = ['id']


class ContactoClienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactoCliente
        fields = [
            'id', 'nombre', 'cargo', 'telefono', 'email', 'es_principal',
        ]
        read_only_fields = ['id']


class ClienteSerializer(serializers.ModelSerializer):
    direcciones = DireccionClienteSerializer(many=True, read_only=True)
    contactos = ContactoClienteSerializer(many=True, read_only=True)

    class Meta:
        model = Cliente
        fields = [
            'id', 'nombre', 'ruc', 'telefono', 'email',
            'direccion_facturacion', 'direccion_entrega',
            'tipo_cliente', 'sector', 'zona', 'observaciones',
            'limite_credito', 'activo',
            'direcciones', 'contactos',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ClienteListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cliente
        fields = [
            'id', 'nombre', 'ruc', 'telefono', 'email',
            'tipo_cliente', 'activo',
        ]
