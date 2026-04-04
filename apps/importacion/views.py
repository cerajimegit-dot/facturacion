"""Views for Excel import: upload, validate, confirm, status."""
import logging
import pandas as pd
from rest_framework import viewsets, status, mixins
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.permissions import IsEmpresaMember
from .models import ImportJob
from .serializers import ImportJobSerializer, ImportJobUploadSerializer

logger = logging.getLogger('apps.importacion')


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
        logger.info("[views] === INICIO UPLOAD ===")
        print("[views] === INICIO UPLOAD ===")
        
        serializer = ImportJobUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        empresa_id = serializer.validated_data['empresa']
        logger.info(f"[views] upload: empresa_id={empresa_id}")
        print(f"[views] upload: empresa_id={empresa_id}")
        
        # Verify membership
        if not request.user.memberships.filter(
            empresa_id=empresa_id, activo=True
        ).exists():
            logger.warning(f"[views] upload: usuario {request.user} no tiene acceso a empresa {empresa_id}")
            print(f"[views] upload: usuario {request.user} no tiene acceso a empresa {empresa_id}")
            return Response(
                {'detail': 'No tiene acceso a esta empresa.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        # Count rows in the Excel file
        archivo = serializer.validated_data['archivo']
        tipo = serializer.validated_data['tipo']
        total_filas = 0

        logger.info(f"[views] upload: leyendo archivo {archivo.name}, tipo={tipo}")
        print(f"[views] upload: leyendo archivo {archivo.name}, tipo={tipo}")
        
        try:
            if tipo == 'mixto':
                xls = pd.ExcelFile(archivo)
                for sheet_name in xls.sheet_names:
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    total_filas += len(df)
            else:
                df = pd.read_excel(archivo)
                total_filas = len(df)
            
            logger.info(f"[views] upload: total_filas={total_filas}")
            print(f"[views] upload: total_filas={total_filas}")
        except Exception as e:
            logger.exception(f"[views] ERROR al leer Excel: {e}")
            print(f"[views] ERROR al leer Excel: {e}")
            return Response(
                {'detail': f'Error al leer el archivo Excel: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = ImportJob.objects.create(
            empresa_id=empresa_id,
            usuario=request.user,
            archivo=serializer.validated_data['archivo'],
            tipo=serializer.validated_data['tipo'],
            total_filas=total_filas,
        )

        logger.info(f"[views] upload: job creado id={job.id}, total_filas={total_filas}")
        print(f"[views] upload: job creado id={job.id}, total_filas={total_filas}")
        
        return Response(
            ImportJobSerializer(job).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=['post'])
    def validar(self, request, pk=None):
        """Trigger validation of an uploaded file (synchronous)."""
        logger.info(f"[views.validar] INICIO - pk={pk}")
        print(f"[views.validar] INICIO - pk={pk}")
        
        try:
            job = self.get_object()
            logger.info(f"[views.validar] job obtenido: id={job.id}, estado={job.estado}")
            print(f"[views.validar] job obtenido: id={job.id}, estado={job.estado}")
        except Exception as e:
            logger.exception(f"[views.validar] ERROR al obtener job: {e}")
            print(f"[views.validar] ERROR al obtener job: {e}")
            return Response(
                {'detail': f'Error al obtener el trabajo: {str(e)}'},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        if job.estado not in ('subido', 'error'):
            logger.warning(f"[views.validar] Job {job.id} no puede validarse en estado {job.estado}")
            print(f"[views.validar] Job {job.id} no puede validarse en estado {job.estado}")
            return Response(
                {'detail': 'Solo se pueden validar trabajos en estado "subido" o "error".'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from .tasks import validate_import_task
            logger.info(f"[views.validar] Ejecutando validate_import_task({job.id})")
            print(f"[views.validar] Ejecutando validate_import_task({job.id})")
            result = validate_import_task(str(job.id))
            logger.info(f"[views.validar] validate_import_task completado: {result}")
            print(f"[views.validar] validate_import_task completado: {result}")

            return Response({
                'detail': 'Validación completada.',
                'job_id': str(job.id),
            })
        except Exception as e:
            logger.exception(f"[views.validar] ERROR ejecutando validación: {e}")
            print(f"[views.validar] ERROR ejecutando validación: {e}")
            return Response(
                {'detail': f'Error al validar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        """Execute the import after validation (synchronous)."""
        logger.info(f"[views.confirmar] INICIO - pk={pk}")
        print(f"[views.confirmar] INICIO - pk={pk}")
        
        try:
            job = self.get_object()
            logger.info(f"[views.confirmar] job obtenido: id={job.id}, estado={job.estado}")
            print(f"[views.confirmar] job obtenido: id={job.id}, estado={job.estado}")
        except Exception as e:
            logger.exception(f"[views.confirmar] ERROR al obtener job: {e}")
            print(f"[views.confirmar] ERROR al obtener job: {e}")
            return Response(
                {'detail': f'Error al obtener el trabajo: {str(e)}'},
                status=status.HTTP_404_NOT_FOUND,
            )
        
        if job.estado != 'validado':
            logger.warning(f"[views.confirmar] Job {job.id} no puede confirmarse en estado {job.estado}")
            print(f"[views.confirmar] Job {job.id} no puede confirmarse en estado {job.estado}")
            return Response(
                {'detail': 'El trabajo debe estar validado antes de confirmar la importación.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from .tasks import execute_import_task
            logger.info(f"[views.confirmar] Ejecutando execute_import_task({job.id})")
            print(f"[views.confirmar] Ejecutando execute_import_task({job.id})")
            result = execute_import_task(str(job.id))
            logger.info(f"[views.confirmar] execute_import_task completado: {result}")
            print(f"[views.confirmar] execute_import_task completado: {result}")

            return Response({
                'detail': 'Importación completada.',
                'job_id': str(job.id),
            })
        except Exception as e:
            logger.exception(f"[views.confirmar] ERROR ejecutando importación: {e}")
            print(f"[views.confirmar] ERROR ejecutando importación: {e}")
            return Response(
                {'detail': f'Error al importar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancel an import job."""
        job = self.get_object()
        logger.info(f"[views] Cancelar job {job.id}: estado={job.estado}")
        print(f"[views] Cancelar job {job.id}: estado={job.estado}")
        
        if job.estado in ('completado', 'cancelado'):
            logger.warning(f"[views] Job {job.id} no puede cancelarse en estado {job.estado}")
            print(f"[views] Job {job.id} no puede cancelarse en estado {job.estado}")
            return Response(
                {'detail': 'No se puede cancelar este trabajo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        job.estado = 'cancelado'
        job.save(update_fields=['estado'])
        logger.info(f"[views] Job {job.id} cancelado")
        print(f"[views] Job {job.id} cancelado")
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
