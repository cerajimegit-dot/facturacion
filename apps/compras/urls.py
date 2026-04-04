"""URL routes for compras app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ProveedorViewSet, CategoriaGastoViewSet, 
    CompraViewSet, CompraDetalleViewSet, GastoViewSet
)

router = DefaultRouter()
router.register('proveedores', ProveedorViewSet, basename='proveedor')
router.register('categorias-gasto', CategoriaGastoViewSet, basename='categoriagasto')
router.register('compras', CompraViewSet, basename='compra')
router.register('compra-detalles', CompraDetalleViewSet, basename='compradetalle')
router.register('gastos', GastoViewSet, basename='gasto')

urlpatterns = [
    path('', include(router.urls)),
]
