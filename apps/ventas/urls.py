"""URL routes for ventas app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CotizacionViewSet, VentaViewSet, CuentaPorCobrarViewSet,
    RegistroPagoViewSet, NotaCreditoViewSet,
)

router = DefaultRouter()
router.register('cotizaciones', CotizacionViewSet, basename='cotizacion')
router.register('cuentas-por-cobrar', CuentaPorCobrarViewSet, basename='cuentaporcobrar')
router.register('pagos', RegistroPagoViewSet, basename='registro-pago')
router.register('notas-credito', NotaCreditoViewSet, basename='nota-credito')
router.register('', VentaViewSet, basename='venta')

urlpatterns = [
    path('', include(router.urls)),
]
