"""Serializers for Contrato and OrdenServicio."""
from rest_framework import serializers
from .models import Contrato, OrdenServicio


class ContratoSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)

    class Meta:
        model = Contrato
        fields = [
            'id', 'numero', 'cliente', 'cliente_nombre',
            'descripcion', 'fecha_inicio', 'fecha_fin',
            'estado', 'monto_recurrente', 'moneda',
            'frecuencia_cobro', 'terminos', 'notas',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class OrdenServicioSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source='cliente.nombre', read_only=True)
    contrato_numero = serializers.CharField(source='contrato.numero', read_only=True)

    class Meta:
        model = OrdenServicio
        fields = [
            'id', 'numero', 'contrato', 'contrato_numero',
            'cliente', 'cliente_nombre',
            'descripcion', 'estado', 'prioridad',
            'fecha_programada', 'fecha_completada',
            'asignado_a', 'notas',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
