"""Serializers for Empresa model."""
from rest_framework import serializers
from .models import Empresa


class EmpresaSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Empresa
        fields = [
            'id', 'codigo', 'nombre', 'ruc', 'razon_social',
            'direccion', 'telefono', 'email', 'logo', 'logo_url',
            'moneda_principal', 'activa', 'configuracion',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url
        return None


class EmpresaListSerializer(serializers.ModelSerializer):
    logo_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Empresa
        fields = [
            'id', 'codigo', 'nombre', 'ruc', 'telefono', 'email',
            'direccion', 'moneda_principal', 'activa', 'razon_social', 'logo_url',
        ]
    
    def get_logo_url(self, obj):
        if obj.logo:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.logo.url) if request else obj.logo.url
        return None
