"""Serializers for Empresa model."""
from rest_framework import serializers
from .models import Empresa


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = [
            'id', 'codigo', 'nombre', 'ruc', 'razon_social',
            'direccion', 'telefono', 'email', 'logo',
            'moneda_principal', 'activa', 'configuracion',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EmpresaListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = [
            'id', 'codigo', 'nombre', 'ruc', 'telefono', 'email',
            'direccion', 'moneda_principal', 'activa', 'razon_social',
        ]
