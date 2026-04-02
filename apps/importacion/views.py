"""Views for Excel import: upload, validate, confirm, status."""
from rest_framework import viewsets, status, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.permissions import IsEmpresaMember
from .models import ImportJob
from .serializers import ImportJobSerializer, ImportJobUploadSerializer


class ImportJobViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Manage import jobs: upload, validate, confirm import, check status."""
    serializer_class = ImportJobSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ImportJob.objects.select_related('empresa', 'usuario')
        empresa_id = self.request.query_params.get('empresa')
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        return qs.filter(
            empresa__memberships__usuario=self.request.user,
            empresa__memberships__activo=True,
        ).distinct()

    @action(detail=False, methods=['post'])
    def upload(self, request):
        """Upload an Excel file and create an import job."""
        serializer = ImportJobUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        empresa_id = serializer.validated_data['empresa']
        # Verify membership
        if not request.user.memberships.filter(
            empresa_id=empresa_id, activo=True
        ).exists():
            return Response(
                {'detail': 'No tiene acceso a esta empresa.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        job = ImportJob.objects.create(
            empresa_id=empresa_id,
            usuario=request.user,
            archivo=serializer.validated_data['archivo'],
            tipo=serializer.validated_data['tipo'],
        )

        return Response(
            ImportJobSerializer(job).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def validar(self, request, pk=None):
        """Trigger async validation of an uploaded file."""
        job = self.get_object()
        if job.estado not in ('subido', 'error'):
            return Response(
                {'detail': 'Solo se pueden validar trabajos en estado "subido" o "error".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .tasks import validate_import_task
        result = validate_import_task.delay(str(job.id))
        job.task_id = result.id
        job.save(update_fields=['task_id'])

        return Response({
            'detail': 'Validación iniciada.',
            'job_id': str(job.id),
            'task_id': result.id,
        })

    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        """Confirm and execute the import after validation."""
        job = self.get_object()
        if job.estado != 'validado':
            return Response(
                {'detail': 'El trabajo debe estar validado antes de confirmar la importación.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from .tasks import execute_import_task
        result = execute_import_task.delay(str(job.id))
        job.task_id = result.id
        job.save(update_fields=['task_id'])

        return Response({
            'detail': 'Importación iniciada.',
            'job_id': str(job.id),
            'task_id': result.id,
        })

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancel an import job."""
        job = self.get_object()
        if job.estado in ('completado', 'cancelado'):
            return Response(
                {'detail': 'No se puede cancelar este trabajo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        job.estado = 'cancelado'
        job.save(update_fields=['estado'])
        return Response(ImportJobSerializer(job).data)

    @action(detail=True, methods=['get'])
    def reporte(self, request, pk=None):
        """Get the full validation/error report for a job."""
        job = self.get_object()
        return Response({
            'id': str(job.id),
            'estado': job.estado,
            'total_filas': job.total_filas,
            'filas_validas': job.filas_validas,
            'filas_warnings': job.filas_warnings,
            'filas_errores': job.filas_errores,
            'filas_importadas': job.filas_importadas,
            'reporte_validacion': job.reporte_validacion,
            'reporte_errores': job.reporte_errores,
            'mensaje': job.mensaje,
        })
