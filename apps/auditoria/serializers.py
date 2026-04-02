"""Serializers for Auditoria."""
from rest_framework import serializers
from .models import Auditoria


class AuditoriaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)

    class Meta:
        model = Auditoria
        fields = [
            'id', 'usuario', 'usuario_nombre',
            'empresa', 'empresa_nombre',
            'accion', 'modelo', 'objeto_id',
            'datos_anteriores', 'datos_nuevos',
            'ip_address', 'timestamp', 'descripcion',
        ]
        read_only_fields = fields
