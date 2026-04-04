"""Views for Producto, Categoria management."""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters import FilterSet, CharFilter, BooleanFilter, ModelChoiceFilter
from django_filters.rest_framework import DjangoFilterBackend
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


class ProductoFilterSet(FilterSet):
    """Explicit FilterSet for Producto to properly handle DecimalFields."""
    class Meta:
        model = Producto
        fields = {
            'tipo': ['exact'],
            'categoria': ['exact'],
            'activo': ['exact'],
        }


class ProductoViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Producto.objects.select_related('categoria').prefetch_related('variantes')
    serializer_class = ProductoSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_class = ProductoFilterSet
    filter_backends = [DjangoFilterBackend]
    search_fields = ['sku', 'nombre', 'descripcion']
    ordering_fields = ['nombre', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductoListSerializer
        return ProductoSerializer


class PrecioListaFilterSet(FilterSet):
    """Explicit FilterSet for PrecioLista to properly handle foreign keys."""
    class Meta:
        model = PrecioLista
        fields = {
            'producto': ['exact'],
            'moneda': ['exact'],
        }


class PrecioListaViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = PrecioLista.objects.select_related('producto')
    serializer_class = PrecioListaSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_class = PrecioListaFilterSet
    filter_backends = [DjangoFilterBackend]
