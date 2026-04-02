"""Views for Producto, Categoria management."""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.core.mixins import TenantQuerySetMixin
from apps.core.permissions import IsEmpresaMember
from .models import Producto, Categoria, PrecioLista
from .serializers import (
    ProductoSerializer, ProductoListSerializer,
    CategoriaSerializer, PrecioListaSerializer,
)


class CategoriaViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    search_fields = ['nombre']


class ProductoViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Producto.objects.select_related('categoria').prefetch_related('variantes')
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['tipo', 'categoria', 'activo']
    search_fields = ['sku', 'nombre', 'descripcion']
    ordering_fields = ['nombre', 'precio_unitario', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductoListSerializer
        return ProductoSerializer


class PrecioListaViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = PrecioLista.objects.select_related('producto')
    serializer_class = PrecioListaSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['producto', 'moneda']
