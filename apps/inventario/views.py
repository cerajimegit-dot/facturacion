"""Views for Inventario management."""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import models, transaction
from apps.core.mixins import TenantQuerySetMixin
from apps.core.permissions import IsEmpresaMember
from .models import Almacen, Stock, MovimientoStock
from .serializers import AlmacenSerializer, StockSerializer, MovimientoStockSerializer


class AlmacenViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Almacen.objects.all()
    serializer_class = AlmacenSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    search_fields = ['codigo', 'nombre']


class StockViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Stock.objects.select_related('producto', 'almacen')
    serializer_class = StockSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['producto', 'almacen']
    search_fields = ['producto__sku', 'producto__nombre']

    @action(detail=False, methods=['get'])
    def bajo_minimo(self, request):
        """List stock items below minimum threshold."""
        empresa = self.get_empresa()
        qs = Stock.objects.filter(
            empresa=empresa, cantidad__lt=models.F('stock_minimo')
        ).select_related('producto', 'almacen')
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)


class MovimientoStockViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = MovimientoStock.objects.select_related('producto', 'almacen', 'usuario')
    serializer_class = MovimientoStockSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['producto', 'almacen', 'tipo']
    ordering_fields = ['created_at']
    http_method_names = ['get', 'post', 'head', 'options']

    @transaction.atomic
    def perform_create(self, serializer):
        empresa = self.get_empresa()
        movimiento = serializer.save(empresa=empresa, usuario=self.request.user)
        stock, created = Stock.objects.get_or_create(
            empresa=empresa,
            producto=movimiento.producto,
            almacen=movimiento.almacen,
            defaults={'cantidad': 0},
        )
        if movimiento.tipo == 'entrada':
            stock.cantidad += movimiento.cantidad
        elif movimiento.tipo == 'salida':
            stock.cantidad -= movimiento.cantidad
        elif movimiento.tipo == 'ajuste':
            stock.cantidad = movimiento.cantidad
        stock.save()
