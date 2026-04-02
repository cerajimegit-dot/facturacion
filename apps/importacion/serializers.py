"""Serializers for ImportJob."""
from rest_framework import serializers
from .models import ImportJob


class ImportJobSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source='usuario.get_full_name', read_only=True)
    empresa_nombre = serializers.CharField(source='empresa.nombre', read_only=True)

    class Meta:
        model = ImportJob
        fields = [
            'id', 'empresa', 'empresa_nombre',
            'usuario', 'usuario_nombre',
            'archivo', 'tipo', 'estado',
            'total_filas', 'filas_validas', 'filas_warnings',
            'filas_errores', 'filas_importadas',
            'reporte_validacion', 'reporte_errores',
            'archivo_errores', 'mensaje',
            'iniciado_en', 'finalizado_en',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'usuario', 'estado',
            'total_filas', 'filas_validas', 'filas_warnings',
            'filas_errores', 'filas_importadas',
            'reporte_validacion', 'reporte_errores',
            'archivo_errores', 'mensaje',
            'iniciado_en', 'finalizado_en',
            'created_at', 'updated_at',
        ]


class ImportJobUploadSerializer(serializers.Serializer):
    """Serializer for uploading an Excel file for import."""
    archivo = serializers.FileField()
    tipo = serializers.ChoiceField(choices=ImportJob.TIPO_CHOICES)
    empresa = serializers.UUIDField()

    def validate_archivo(self, value):
        allowed_extensions = ['.xlsx', '.xls']
        ext = value.name.lower().split('.')[-1]
        if f'.{ext}' not in allowed_extensions:
            raise serializers.ValidationError(
                'Solo se permiten archivos Excel (.xlsx, .xls)'
            )
        if value.size > 52428800:  # 50 MB
            raise serializers.ValidationError(
                'El archivo no puede exceder 50 MB'
            )
        return value
