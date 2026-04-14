"""Views para el módulo de Activos Fijos."""
from rest_framework import viewsets, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction, IntegrityError
from django.utils import timezone

from apps.core.mixins import TenantQuerySetMixin
from apps.core.permissions import IsEmpresaMember

from .models import (
    ClasificacionActivo, UbicacionActivo, CentroCosto,
    ActivoFijo, MovimientoActivo, MantenimientoActivo,
    BajaActivo, DepreciacionMensual, ProcesoDepreciacion,
)
from .serializers import (
    ClasificacionActivoSerializer, UbicacionActivoSerializer,
    CentroCostoSerializer, ActivoFijoSerializer, ActivoFijoListSerializer,
    MovimientoActivoSerializer, MantenimientoActivoSerializer,
    BajaActivoSerializer, DepreciacionMensualSerializer,
    ProcesoDepreciacionSerializer,
)
from .services import ActivoFijoService


class _IntegrityMixin:
    """Catch IntegrityError on create/update and return 400 instead of 500."""
    def perform_create(self, serializer):
        try:
            super().perform_create(serializer)
        except IntegrityError as e:
            raise serializers.ValidationError({'detail': 'Ya existe un registro con estos datos. Verifique campos únicos.'})

    def perform_update(self, serializer):
        try:
            super().perform_update(serializer)
        except IntegrityError:
            raise serializers.ValidationError({'detail': 'Ya existe un registro con estos datos. Verifique campos únicos.'})


class ClasificacionActivoViewSet(_IntegrityMixin, TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = ClasificacionActivo.objects.select_related(
        'cuenta_activo', 'cuenta_depreciacion_acumulada',
        'cuenta_gasto_depreciacion', 'cuenta_resultado_baja',
    )
    serializer_class = ClasificacionActivoSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    search_fields = ['nombre']


class UbicacionActivoViewSet(_IntegrityMixin, TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = UbicacionActivo.objects.all()
    serializer_class = UbicacionActivoSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    search_fields = ['planta', 'edificio', 'area']


class CentroCostoViewSet(_IntegrityMixin, TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = CentroCosto.objects.all()
    serializer_class = CentroCostoSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    search_fields = ['codigo', 'descripcion']


class ActivoFijoViewSet(_IntegrityMixin, TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = ActivoFijo.objects.select_related(
        'clasificacion', 'ubicacion', 'centro_costo', 'proveedor', 'responsable'
    )
    serializer_class = ActivoFijoSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['tipo', 'estado', 'clasificacion', 'ubicacion', 'centro_costo', 'responsable']
    search_fields = ['codigo', 'nombre', 'numero_serie', 'descripcion']
    ordering_fields = ['codigo', 'nombre', 'valor_adquisicion', 'fecha_adquisicion', 'valor_libro']

    def get_serializer_class(self):
        if self.action == 'list':
            return ActivoFijoListSerializer
        return ActivoFijoSerializer

    def update(self, request, *args, **kwargs):
        """Bloquear edición de valor_adquisicion si el activo ya fue activado."""
        activo = self.get_object()
        if activo.estado == 'baja':
            return Response(
                {'detail': 'No se puede modificar un activo dado de baja.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if activo.fecha_activacion and 'valor_adquisicion' in request.data:
            if str(request.data['valor_adquisicion']) != str(activo.valor_adquisicion):
                return Response(
                    {'detail': 'No se permite modificar el valor de adquisición después de la activación.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Solo permitir eliminar activos nunca activados."""
        activo = self.get_object()
        if activo.estado != 'activo' or activo.depreciacion_acumulada > 0:
            return Response(
                {'detail': 'Use la función de baja para desincorporar activos. Solo se pueden eliminar activos sin depreciación.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Dashboard KPIs de activos fijos."""
        empresa = self.get_empresa()
        resumen = ActivoFijoService.obtener_resumen_activos(empresa)
        for k, v in resumen.items():
            if hasattr(v, 'quantize'):
                resumen[k] = str(v)
        return Response(resumen)

    @action(detail=False, methods=['get'])
    def alertas(self, request):
        """Activos que superan vida útil o tienen mantenimientos pendientes."""
        empresa = self.get_empresa()
        activos = ActivoFijo.objects.filter(
            empresa=empresa,
            estado__in=['activo', 'en_mantenimiento'],
        ).select_related('clasificacion', 'ubicacion', 'responsable')

        alertas = []
        for a in activos:
            if a.supera_vida_util:
                alertas.append({
                    'activo_id': str(a.id),
                    'codigo': a.codigo,
                    'nombre': a.nombre,
                    'tipo_alerta': 'vida_util_superada',
                    'mensaje': f'Activo {a.codigo} superó su vida útil de {a.vida_util_anios} años.',
                })
            mant_pendientes = a.mantenimientos.filter(estado__in=['programado', 'en_proceso']).count()
            if mant_pendientes > 0:
                alertas.append({
                    'activo_id': str(a.id),
                    'codigo': a.codigo,
                    'nombre': a.nombre,
                    'tipo_alerta': 'mantenimiento_pendiente',
                    'mensaje': f'Activo {a.codigo} tiene {mant_pendientes} mantenimiento(s) pendiente(s).',
                })
        return Response(alertas)

    @action(detail=True, methods=['post'])
    def mover(self, request, pk=None):
        """Mover activo a nueva ubicación/responsable."""
        activo = self.get_object()
        ubicacion_destino_id = request.data.get('ubicacion_destino')
        responsable_nuevo_id = request.data.get('responsable_nuevo')
        motivo = request.data.get('motivo', '')

        if not ubicacion_destino_id:
            return Response(
                {'detail': 'ubicacion_destino es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            ubicacion_destino = UbicacionActivo.objects.get(
                id=ubicacion_destino_id, empresa=activo.empresa
            )
        except UbicacionActivo.DoesNotExist:
            return Response(
                {'detail': 'Ubicación destino no encontrada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        responsable_nuevo = None
        if responsable_nuevo_id:
            from apps.usuarios.models import Usuario
            try:
                responsable_nuevo = Usuario.objects.get(id=responsable_nuevo_id)
            except Usuario.DoesNotExist:
                return Response(
                    {'detail': 'Responsable no encontrado.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            ActivoFijoService.mover_activo(
                activo, ubicacion_destino, responsable_nuevo, motivo, request.user
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ActivoFijoSerializer(activo).data)

    @action(detail=True, methods=['post'])
    def dar_baja(self, request, pk=None):
        """Dar de baja un activo fijo."""
        activo = self.get_object()
        fecha_baja = request.data.get('fecha_baja')
        motivo = request.data.get('motivo', 'otro')
        motivo_detalle = request.data.get('motivo_detalle', '')
        valor_rescate = request.data.get('valor_rescate', 0)
        autorizado_por_id = request.data.get('autorizado_por')

        if not fecha_baja:
            return Response(
                {'detail': 'fecha_baja es requerida.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        autorizado_por = None
        if autorizado_por_id:
            from apps.usuarios.models import Usuario
            try:
                autorizado_por = Usuario.objects.get(id=autorizado_por_id)
            except Usuario.DoesNotExist:
                pass

        try:
            from decimal import Decimal
            ActivoFijoService.dar_de_baja(
                activo, fecha_baja, motivo, motivo_detalle,
                Decimal(str(valor_rescate)), request.user, autorizado_por
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(ActivoFijoSerializer(activo).data)

    @action(detail=False, methods=['post'])
    def calcular_depreciacion(self, request):
        """Calcular depreciación mensual para la empresa."""
        empresa = self.get_empresa()
        anio = request.data.get('anio')
        mes = request.data.get('mes')

        if not anio or not mes:
            hoy = timezone.now().date()
            anio = anio or hoy.year
            mes = mes or hoy.month

        try:
            anio = int(anio)
            mes = int(mes)
            if not (1 <= mes <= 12):
                raise ValueError()
        except (ValueError, TypeError):
            return Response(
                {'detail': 'Año y mes deben ser números válidos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            registros = ActivoFijoService.calcular_depreciacion_mensual(
                empresa, anio, mes, usuario=request.user
            )
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'mensaje': f'Depreciación calculada para {mes:02d}/{anio}.',
            'registros_creados': registros,
        })


class MovimientoActivoViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = MovimientoActivo.objects.select_related(
        'activo', 'ubicacion_origen', 'ubicacion_destino', 'usuario_registro'
    )
    serializer_class = MovimientoActivoSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['activo']
    search_fields = ['activo__codigo', 'activo__nombre', 'motivo']
    ordering_fields = ['fecha']
    http_method_names = ['get', 'head', 'options']


class MantenimientoActivoViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = MantenimientoActivo.objects.select_related('activo', 'usuario')
    serializer_class = MantenimientoActivoSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['activo', 'tipo', 'estado']
    search_fields = ['activo__codigo', 'activo__nombre', 'descripcion']
    ordering_fields = ['fecha', 'tipo', 'estado']

    def perform_create(self, serializer):
        empresa = self.get_empresa()
        activo = serializer.validated_data.get('activo')

        if activo and activo.estado == 'baja':
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'activo': 'No se puede registrar mantenimiento en un activo dado de baja.'})

        serializer.save(empresa=empresa, usuario=self.request.user)

        if activo and activo.estado != 'en_mantenimiento' and activo.estado != 'baja':
            activo.estado = 'en_mantenimiento'
            activo.save(update_fields=['estado', 'updated_at'])

    @action(detail=True, methods=['post'])
    def completar(self, request, pk=None):
        """Completar un mantenimiento."""
        mantenimiento = self.get_object()
        try:
            ActivoFijoService.completar_mantenimiento(mantenimiento, request.user)
        except ValueError as e:
            return Response({'detail': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MantenimientoActivoSerializer(mantenimiento).data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancelar un mantenimiento programado."""
        mantenimiento = self.get_object()
        if mantenimiento.estado == 'completado':
            return Response(
                {'detail': 'No se puede cancelar un mantenimiento completado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        mantenimiento.estado = 'cancelado'
        mantenimiento.save(update_fields=['estado', 'updated_at'])

        activo = mantenimiento.activo
        pendientes = activo.mantenimientos.filter(estado__in=['programado', 'en_proceso']).count()
        if pendientes == 0 and activo.estado == 'en_mantenimiento':
            activo.estado = 'activo'
            activo.save(update_fields=['estado', 'updated_at'])

        return Response(MantenimientoActivoSerializer(mantenimiento).data)


class BajaActivoViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = BajaActivo.objects.select_related('activo', 'usuario', 'autorizado_por')
    serializer_class = BajaActivoSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['motivo']
    search_fields = ['activo__codigo', 'activo__nombre', 'motivo_detalle']
    ordering_fields = ['fecha_baja']
    http_method_names = ['get', 'head', 'options']


class DepreciacionMensualViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = DepreciacionMensual.objects.select_related('activo')
    serializer_class = DepreciacionMensualSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['activo', 'anio', 'mes']
    ordering_fields = ['anio', 'mes']
    http_method_names = ['get', 'head', 'options']

    @action(detail=False, methods=['get'])
    def reporte(self, request):
        """Reporte de depreciación por período."""
        empresa = self.get_empresa()
        anio = request.query_params.get('anio')
        mes = request.query_params.get('mes')

        qs = DepreciacionMensual.objects.filter(empresa=empresa).select_related('activo')
        if anio:
            qs = qs.filter(anio=int(anio))
        if mes:
            qs = qs.filter(mes=int(mes))

        from django.db.models import Sum
        totales = qs.aggregate(total_depreciacion=Sum('monto'))

        serializer = self.get_serializer(qs, many=True)
        return Response({
            'registros': serializer.data,
            'total_depreciacion': str(totales['total_depreciacion'] or 0),
        })


class ProcesoDepreciacionViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = ProcesoDepreciacion.objects.all()
    serializer_class = ProcesoDepreciacionSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['anio', 'mes', 'estado']
    ordering_fields = ['anio', 'mes']
    http_method_names = ['get', 'head', 'options']
