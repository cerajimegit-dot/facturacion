"""Views para gestión de compras y gastos."""
from rest_framework import viewsets, status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from apps.core.mixins import TenantQuerySetMixin
from apps.core.permissions import IsEmpresaMember
from .models import Proveedor, Compra, CompraDetalle, Gasto, CategoriaGasto
from .serializers import (
    ProveedorSerializer, ProveedorListSerializer,
    CompraSerializer, CompraDetailedSerializer, CompraListSerializer,
    CompraDetalleSerializer, GastoSerializer, CategoriaGastoSerializer
)


class ProveedorViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD de proveedores."""
    queryset = Proveedor.objects.all()
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    search_fields = ['nombre', 'ruc_numero', 'email', 'pais']
    filterset_fields = ['activo', 'pais', 'importancia']
    ordering_fields = ['nombre', 'created_at']
    ordering = ['nombre']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProveedorListSerializer
        return ProveedorSerializer

    @action(detail=True, methods=['get'])
    def historial_compras(self, request, pk=None):
        """Historial de compras con este proveedor."""
        proveedor = self.get_object()
        compras = Compra.objects.filter(
            empresa=self.get_empresa(),
            proveedor=proveedor
        ).order_by('-fecha')
        serializer = CompraListSerializer(compras, many=True)
        return Response({
            'proveedor': proveedor.nombre,
            'total_compras': compras.count(),
            'compras': serializer.data
        })


class CategoriaGastoViewSet(viewsets.ModelViewSet):
    """CRUD de categorías de gasto."""
    queryset = CategoriaGasto.objects.filter(activo=True)
    serializer_class = CategoriaGastoSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ['nombre']
    filterset_fields = ['activo']


class CompraViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD y operaciones de compras."""
    queryset = Compra.objects.select_related('proveedor', 'almacen', 'usuario_registra', 'usuario_recepcion')
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    search_fields = ['numero', 'proveedor__nombre']
    filterset_fields = ['estado', 'moneda', 'proveedor', 'almacen']
    ordering_fields = ['fecha', 'created_at', 'total']
    ordering = ['-fecha']

    def get_serializer_class(self):
        if self.action == 'list':
            return CompraListSerializer
        elif self.action in ['retrieve']:
            return CompraDetailedSerializer
        return CompraSerializer

    def perform_create(self, serializer):
        """Registrar usuario al crear compra."""
        empresa = self.get_empresa()
        serializer.save(
            empresa=empresa,
            usuario_registra=self.request.user
        )

    @transaction.atomic
    def perform_update(self, serializer):
        """Actualizar solo compras pendientes."""
        compra = serializer.instance
        if compra.estado != 'pendiente':
            raise serializers.ValidationError(
                "Solo se pueden editar compras en estado Pendiente"
            )
        serializer.save()

    @action(detail=True, methods=['post'])
    def recibir(self, request, pk=None):
        """Recibir productos de la compra e ingresarlos a inventario."""
        compra = self.get_object()
        
        if compra.estado != 'pendiente':
            return Response(
                {'error': 'Solo se pueden recibir compras en estado Pendiente'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not compra.detalles.exists():
            return Response(
                {'error': 'La compra debe tener detalles antes de recibir'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                # Ingresar productos al stock
                from apps.inventario.models import Stock, MovimientoStock

                for detalle in compra.detalles.filter(producto__isnull=False):
                    # Crear o actualizar stock
                    stock, created = Stock.objects.get_or_create(
                        empresa=compra.empresa,
                        producto=detalle.producto,
                        almacen=compra.almacen,
                        defaults={'cantidad': 0}
                    )
                    stock.cantidad += detalle.cantidad
                    stock.save()

                    # Registrar movimiento con trazabilidad a compra
                    MovimientoStock.objects.create(
                        empresa=compra.empresa,
                        producto=detalle.producto,
                        almacen=compra.almacen,
                        tipo='entrada',
                        cantidad=detalle.cantidad,
                        referencia=f"Compra #{compra.numero}",
                        usuario=request.user,
                        nota=f"Recepción de compra {compra.numero} a proveedor {compra.proveedor.nombre}"
                    )

                # Actualizar compra
                compra.estado = 'recepcionada'
                compra.fecha_recepcion = timezone.now()
                compra.usuario_recepcion = request.user
                compra.save()

                return Response({
                    'status': 'success',
                    'mensaje': f'Compra #{compra.numero} recepcionada exitosamente',
                    'compra': CompraDetailedSerializer(compra).data
                })

        except Exception as e:
            return Response(
                {'error': f'Error al recibir compra: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        """Cancelar compra pendiente."""
        compra = self.get_object()
        
        if compra.estado != 'pendiente':
            return Response(
                {'error': 'Solo se pueden cancelar compras en estado Pendiente'},
                status=status.HTTP_400_BAD_REQUEST
            )

        compra.estado = 'cancelada'
        compra.save()

        return Response({
            'status': 'success',
            'mensaje': f'Compra #{compra.numero} cancelada'
        })

    @action(detail=False, methods=['get'])
    def resumen_mes(self, request):
        """Resumen de compras del mes actual."""
        from django.utils import timezone
        from datetime import timedelta
        import datetime

        empresa = self.get_empresa()
        ahora = timezone.now()
        inicio_mes = datetime.datetime(ahora.year, ahora.month, 1)
        
        compras_mes = Compra.objects.filter(
            empresa=empresa,
            fecha__gte=inicio_mes,
            estado='recepcionada'
        )
        
        total_mes = sum(c.total for c in compras_mes)
        cantidad_compras = compras_mes.count()
        
        return Response({
            'mes': ahora.month,
            'año': ahora.year,
            'total_mes': float(total_mes),
            'cantidad_compras': cantidad_compras,
            'promedio_compra': float(total_mes / cantidad_compras) if cantidad_compras > 0 else 0
        })


class CompraDetalleViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD de detalles de compra."""
    queryset = CompraDetalle.objects.select_related('compra', 'producto', 'categoria_gasto')
    serializer_class = CompraDetalleSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['compra', 'es_servicio']
    ordering = ['compra', 'created_at']

    @transaction.atomic
    def perform_create(self, serializer):
        """Crear detalle y actualizar totales de compra."""
        empresa = self.get_empresa()
        detalle = serializer.save(empresa=empresa)
        
        # Actualizar totales de compra
        compra = detalle.compra
        detalles = compra.detalles.all()
        
        if detalles.exists():
            compra.subtotal = sum(d.subtotal for d in detalles)
            compra.impuestos_total = sum(d.impuestos for d in detalles)
            compra.total = sum(d.total for d in detalles)
            compra.save()


class GastoViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD de gastos generales."""
    queryset = Gasto.objects.select_related('categoria', 'usuario')
    serializer_class = GastoSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['categoria', 'moneda', 'aprobado']
    ordering_fields = ['fecha', 'monto', 'created_at']
    ordering = ['-fecha']

    def perform_create(self, serializer):
        """Asignar usuario actual al crear gasto."""
        empresa = self.get_empresa()
        serializer.save(empresa=empresa, usuario=self.request.user)

    @action(detail=True, methods=['post'])
    def aprobar(self, request, pk=None):
        """Aprobar gasto."""
        gasto = self.get_object()
        gasto.aprobado = True
        gasto.save()
        return Response({'status': 'Gasto aprobado'})

    @action(detail=False, methods=['get'])
    def resumen_categoria(self, request):
        """Resumen de gastos por categoría del mes actual."""
        from django.db.models import Sum
        from django.utils import timezone
        import datetime

        empresa = self.get_empresa()
        ahora = timezone.now()
        inicio_mes = datetime.datetime(ahora.year, ahora.month, 1)

        gastos = Gasto.objects.filter(
            empresa=empresa,
            fecha__gte=inicio_mes
        ).values('categoria__nombre').annotate(total=Sum('monto')).order_by('-total')

        return Response({
            'mes': ahora.month,
            'año': ahora.year,
            'gastos_por_categoria': list(gastos)
        })
