"""URL routes for inventario app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AlmacenViewSet, StockViewSet, MovimientoStockViewSet

router = DefaultRouter()
router.register('almacenes', AlmacenViewSet, basename='almacen')
router.register('movimientos', MovimientoStockViewSet, basename='movimientostock')
router.register('', StockViewSet, basename='stock')

urlpatterns = [
    path('', include(router.urls)),
]
