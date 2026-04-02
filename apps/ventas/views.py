"""Views for Ventas, Cotizaciones, and Cuentas por Cobrar."""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from apps.core.mixins import TenantQuerySetMixin
from apps.core.permissions import IsEmpresaMember
from .models import Cotizacion, LineaCotizacion, Venta, LineaVenta, CuentaPorCobrar
from .serializers import (
    CotizacionSerializer, LineaCotizacionSerializer,
    VentaSerializer, VentaListSerializer, LineaVentaSerializer,
    CuentaPorCobrarSerializer,
)


class CotizacionViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Cotizacion.objects.select_related('cliente', 'vendedor').prefetch_related('lineas')
    serializer_class = CotizacionSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['estado', 'cliente']
    search_fields = ['numero', 'cliente__nombre']
    ordering_fields = ['fecha', 'numero', 'total']

    @action(detail=True, methods=['post'])
    def agregar_linea(self, request, pk=None):
        cotizacion = self.get_object()
        serializer = LineaCotizacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(cotizacion=cotizacion)
        cotizacion.subtotal = sum(l.subtotal for l in cotizacion.lineas.all())
        cotizacion.impuestos = sum(l.impuesto_monto for l in cotizacion.lineas.all())
        cotizacion.total = cotizacion.subtotal + cotizacion.impuestos
        cotizacion.save(update_fields=['subtotal', 'impuestos', 'total'])
        return Response(LineaCotizacionSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def convertir_a_venta(self, request, pk=None):
        """Convert accepted quotation into a sale."""
        cotizacion = self.get_object()
        if cotizacion.estado != 'aceptada':
            return Response(
                {'detail': 'Solo se pueden convertir cotizaciones aceptadas.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            venta = Venta.objects.create(
                empresa=cotizacion.empresa,
                numero=f"V-{cotizacion.numero}",
                cliente=cotizacion.cliente,
                cotizacion=cotizacion,
                fecha=cotizacion.fecha,
                fecha_vencimiento=cotizacion.fecha_vencimiento,
                moneda=cotizacion.moneda,
                vendedor=cotizacion.vendedor,
            )
            for lc in cotizacion.lineas.all():
                LineaVenta.objects.create(
                    venta=venta,
                    producto=lc.producto,
                    descripcion=lc.descripcion,
                    cantidad=lc.cantidad,
                    precio_unitario=lc.precio_unitario,
                    descuento_porcentaje=lc.descuento_porcentaje,
                    impuesto_porcentaje=lc.impuesto_porcentaje,
                )
            venta.recalcular_totales()
        return Response(VentaSerializer(venta).data, status=status.HTTP_201_CREATED)


class VentaViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Venta.objects.select_related('cliente', 'vendedor').prefetch_related('lineas')
    serializer_class = VentaSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['estado', 'cliente', 'moneda']
    search_fields = ['numero', 'cliente__nombre', 'cliente__ruc']
    ordering_fields = ['fecha', 'numero', 'total']

    def get_serializer_class(self):
        if self.action == 'list':
            return VentaListSerializer
        return VentaSerializer

    @action(detail=True, methods=['post'])
    def agregar_linea(self, request, pk=None):
        venta = self.get_object()
        if venta.estado in ('anulada', 'pagada'):
            return Response(
                {'detail': 'No se pueden agregar líneas a una venta anulada o pagada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = LineaVentaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(venta=venta)
        venta.recalcular_totales()
        return Response(LineaVentaSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        venta = self.get_object()
        if venta.estado != 'borrador':
            return Response(
                {'detail': 'Solo se pueden confirmar ventas en borrador.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            venta.estado = 'confirmada'
            venta.saldo_pendiente = venta.total
            venta.save(update_fields=['estado', 'saldo_pendiente'])
            CuentaPorCobrar.objects.create(
                empresa=venta.empresa,
                venta=venta,
                cliente=venta.cliente,
                monto_original=venta.total,
                saldo=venta.total,
                moneda=venta.moneda,
                fecha_emision=venta.fecha,
                fecha_vencimiento=venta.fecha_vencimiento or venta.fecha,
            )
        return Response(VentaSerializer(venta).data)

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        venta = self.get_object()
        if venta.estado == 'anulada':
            return Response(
                {'detail': 'La venta ya está anulada.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        venta.estado = 'anulada'
        venta.save(update_fields=['estado'])
        venta.cuentas_por_cobrar.update(estado='pagada', saldo=0)
        return Response(VentaSerializer(venta).data)


class CuentaPorCobrarViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = CuentaPorCobrar.objects.select_related('venta', 'cliente')
    serializer_class = CuentaPorCobrarSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['estado', 'cliente', 'moneda']
    search_fields = ['venta__numero', 'cliente__nombre']
    ordering_fields = ['fecha_vencimiento', 'saldo']

    @action(detail=False, methods=['get'])
    def vencidas(self, request):
        """List overdue accounts."""
        from django.utils import timezone
        empresa = self.get_empresa()
        qs = CuentaPorCobrar.objects.filter(
            empresa=empresa,
            fecha_vencimiento__lt=timezone.now().date(),
            estado__in=['pendiente', 'parcial'],
        ).select_related('venta', 'cliente')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def resumen(self, request):
        """Summary of accounts receivable."""
        from django.db.models import Sum, Count
        from django.utils import timezone
        empresa = self.get_empresa()
        qs = CuentaPorCobrar.objects.filter(empresa=empresa)
        total = qs.aggregate(
            total_pendiente=Sum('saldo'),
            cantidad=Count('id'),
        )
        vencidas = qs.filter(
            fecha_vencimiento__lt=timezone.now().date(),
            estado__in=['pendiente', 'parcial'],
        ).aggregate(
            total_vencido=Sum('saldo'),
            cantidad_vencidas=Count('id'),
        )
        return Response({**total, **vencidas})
