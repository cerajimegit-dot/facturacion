"""Views for Ventas, Cotizaciones, Cuentas por Cobrar, and Notas de Crédito."""
from rest_framework import viewsets, status, serializers as drf_serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from apps.core.mixins import TenantQuerySetMixin
from apps.core.permissions import IsEmpresaMember
from .models import (
    Cotizacion, LineaCotizacion, Venta, LineaVenta,
    CuentaPorCobrar, RegistroPago, NotaCredito, LineaNotaCredito,
)
from .serializers import (
    CotizacionSerializer, LineaCotizacionSerializer,
    VentaSerializer, VentaListSerializer, LineaVentaSerializer,
    CuentaPorCobrarSerializer, RegistroPagoSerializer, RegistroPagoCreateSerializer,
    NotaCreditoSerializer, NotaCreditoListSerializer, LineaNotaCreditoSerializer,
)
from .services import VentaService, PagoService


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

    def update(self, request, *args, **kwargs):
        """Bloquear edición de ventas que no estén en borrador.
        Para PATCH (partial=True), permitir observaciones_cobro siempre.
        """
        partial = kwargs.get('partial', False)
        venta = self.get_object()
        if venta.estado != 'borrador':
            if partial:
                campos_editables_siempre = {'observaciones_cobro'}
                campos_solicitados = set(request.data.keys())
                if not campos_solicitados.issubset(campos_editables_siempre):
                    return Response(
                        {'detail': 'Solo se pueden editar ventas en estado borrador (excepto observaciones).'},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            else:
                return Response(
                    {'detail': 'Solo se pueden editar ventas en estado borrador.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """Bloquear eliminación de ventas confirmadas."""
        venta = self.get_object()
        if venta.estado != 'borrador':
            return Response(
                {'detail': 'Solo se pueden eliminar ventas en borrador. Use anulación.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

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
        serializer.save(venta=venta, empresa=venta.empresa)
        venta.recalcular_totales()
        return Response(LineaVentaSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        venta = self.get_object()
        try:
            VentaService.confirmar_venta(venta, usuario=request.user)
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(VentaSerializer(venta).data)

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        venta = self.get_object()
        try:
            VentaService.anular_venta(venta, usuario=request.user)
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
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

    @action(detail=False, methods=['get'])
    def aging(self, request):
        """Aging report por tramos: 0-30, 31-60, 61-90, 90+ días."""
        from django.db.models import Sum, Count, Q, Case, When, DecimalField
        empresa = self.get_empresa()
        hoy = timezone.now().date()

        qs = CuentaPorCobrar.objects.filter(
            empresa=empresa,
            estado__in=['pendiente', 'parcial'],
        )

        tramos = qs.aggregate(
            corriente=Sum(
                Case(
                    When(fecha_vencimiento__gte=hoy, then='saldo'),
                    default=0,
                    output_field=DecimalField(),
                )
            ),
            tramo_0_30=Sum(
                Case(
                    When(
                        fecha_vencimiento__lt=hoy,
                        fecha_vencimiento__gte=hoy - timedelta(days=30),
                        then='saldo',
                    ),
                    default=0,
                    output_field=DecimalField(),
                )
            ),
            tramo_31_60=Sum(
                Case(
                    When(
                        fecha_vencimiento__lt=hoy - timedelta(days=30),
                        fecha_vencimiento__gte=hoy - timedelta(days=60),
                        then='saldo',
                    ),
                    default=0,
                    output_field=DecimalField(),
                )
            ),
            tramo_61_90=Sum(
                Case(
                    When(
                        fecha_vencimiento__lt=hoy - timedelta(days=60),
                        fecha_vencimiento__gte=hoy - timedelta(days=90),
                        then='saldo',
                    ),
                    default=0,
                    output_field=DecimalField(),
                )
            ),
            tramo_90_plus=Sum(
                Case(
                    When(
                        fecha_vencimiento__lt=hoy - timedelta(days=90),
                        then='saldo',
                    ),
                    default=0,
                    output_field=DecimalField(),
                )
            ),
            total_pendiente=Sum('saldo'),
            total_cuentas=Count('id'),
        )

        return Response(tramos)


class RegistroPagoViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """ViewSet for recording partial payments."""
    queryset = RegistroPago.objects.select_related('venta')
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['venta', 'metodo_pago']
    search_fields = ['venta__numero', 'referencia']
    ordering_fields = ['-fecha_pago']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return RegistroPagoCreateSerializer
        return RegistroPagoSerializer
    
    def create(self, request, *args, **kwargs):
        """Create a payment record and update venta totals."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            pago = serializer.save(empresa=self.get_empresa())
            venta = pago.venta
            
            # Update venta totals
            total_pagos = RegistroPago.objects.filter(venta=venta).aggregate(
                total=Sum('monto')
            )['total'] or 0
            
            venta.total_pagado = total_pagos
            venta.saldo_pendiente = venta.total - total_pagos
            
            if venta.saldo_pendiente <= 0:
                venta.estado = 'pagada'
            elif venta.total_pagado > 0:
                venta.estado = 'parcial'
            
            venta.save(update_fields=['total_pagado', 'saldo_pendiente', 'estado'])
        
        return Response(RegistroPagoSerializer(pago).data, status=status.HTTP_201_CREATED)


class NotaCreditoViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """ViewSet para Notas de Crédito."""
    queryset = NotaCredito.objects.select_related('venta_original', 'cliente').prefetch_related('lineas')
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['estado', 'cliente', 'motivo']
    search_fields = ['numero', 'cliente__nombre', 'venta_original__numero']
    ordering_fields = ['fecha', 'numero', 'total']

    def get_serializer_class(self):
        if self.action == 'list':
            return NotaCreditoListSerializer
        return NotaCreditoSerializer

    @action(detail=True, methods=['post'])
    def agregar_linea(self, request, pk=None):
        nc = self.get_object()
        if nc.estado != 'borrador':
            return Response(
                {'detail': 'Solo se pueden agregar líneas a NC en borrador.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = LineaNotaCreditoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(nota_credito=nc, empresa=nc.empresa)
        nc.recalcular_totales()
        return Response(LineaNotaCreditoSerializer(serializer.instance).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        nc = self.get_object()
        try:
            VentaService.confirmar_nota_credito(nc, usuario=request.user)
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(NotaCreditoSerializer(nc).data)
