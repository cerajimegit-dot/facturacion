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
from apps.ventas.services import PagoService


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
        """Confirm a payment and update sale balances + generate accounting entry."""
        pago = self.get_object()
        try:
            PagoService.confirmar_pago(pago, usuario=request.user)
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(PagoSerializer(pago).data)

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        """Void a confirmed payment and reverse balances."""
        pago = self.get_object()
        try:
            PagoService.anular_pago(pago, usuario=request.user)
        except ValueError as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(PagoSerializer(pago).data)
