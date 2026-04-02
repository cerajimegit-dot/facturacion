"""Views for Pago management."""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from apps.core.mixins import TenantQuerySetMixin
from apps.core.permissions import IsEmpresaMember
from .models import Pago
from .serializers import PagoSerializer


class PagoViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Pago.objects.select_related('venta', 'cliente', 'registrado_por')
    serializer_class = PagoSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['venta', 'cliente', 'metodo', 'estado']
    search_fields = ['venta__numero', 'cliente__nombre', 'referencia']
    ordering_fields = ['fecha', 'monto']

    def perform_create(self, serializer):
        empresa = self.get_empresa()
        serializer.save(empresa=empresa, registrado_por=self.request.user)

    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        """Confirm a payment and update sale balances."""
        pago = self.get_object()
        if pago.estado != 'pendiente':
            return Response(
                {'detail': 'Solo se pueden confirmar pagos pendientes.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            pago.estado = 'confirmado'
            pago.save(update_fields=['estado'])
            venta = pago.venta
            venta.total_pagado += pago.monto
            venta.saldo_pendiente = venta.total - venta.total_pagado
            if venta.saldo_pendiente <= 0:
                venta.estado = 'pagada'
                venta.saldo_pendiente = 0
            else:
                venta.estado = 'parcial'
            venta.save(update_fields=['total_pagado', 'saldo_pendiente', 'estado'])
            # Update cuenta por cobrar
            from apps.ventas.models import CuentaPorCobrar
            cxc = CuentaPorCobrar.objects.filter(venta=venta).first()
            if cxc:
                cxc.monto_pagado += pago.monto
                cxc.saldo = cxc.monto_original - cxc.monto_pagado
                if cxc.saldo <= 0:
                    cxc.estado = 'pagada'
                    cxc.saldo = 0
                else:
                    cxc.estado = 'parcial'
                cxc.save(update_fields=['monto_pagado', 'saldo', 'estado'])
        return Response(PagoSerializer(pago).data)

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        """Void a confirmed payment and reverse balances."""
        pago = self.get_object()
        if pago.estado != 'confirmado':
            return Response(
                {'detail': 'Solo se pueden anular pagos confirmados.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            pago.estado = 'anulado'
            pago.save(update_fields=['estado'])
            venta = pago.venta
            venta.total_pagado -= pago.monto
            venta.saldo_pendiente = venta.total - venta.total_pagado
            if venta.total_pagado <= 0:
                venta.estado = 'confirmada'
                venta.total_pagado = 0
            else:
                venta.estado = 'parcial'
            venta.save(update_fields=['total_pagado', 'saldo_pendiente', 'estado'])
            from apps.ventas.models import CuentaPorCobrar
            cxc = CuentaPorCobrar.objects.filter(venta=venta).first()
            if cxc:
                cxc.monto_pagado -= pago.monto
                cxc.saldo = cxc.monto_original - cxc.monto_pagado
                cxc.estado = 'pendiente' if cxc.monto_pagado <= 0 else 'parcial'
                if cxc.monto_pagado < 0:
                    cxc.monto_pagado = 0
                cxc.save(update_fields=['monto_pagado', 'saldo', 'estado'])
        return Response(PagoSerializer(pago).data)
