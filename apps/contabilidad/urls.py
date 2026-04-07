"""URLs para el módulo de contabilidad."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.contabilidad.views import (
    PlanCuentasViewSet, AsientoViewSet, CotizacionDiariaViewSet,
    SaldoCuentaViewSet
)

app_name = 'contabilidad'

router = DefaultRouter()
router.register(r'plan-cuentas', PlanCuentasViewSet, basename='plan-cuentas')
router.register(r'asientos', AsientoViewSet, basename='asientos')
router.register(r'cotizaciones-diarias', CotizacionDiariaViewSet, basename='cotizaciones-diarias')
router.register(r'saldos', SaldoCuentaViewSet, basename='saldos')

urlpatterns = [
    path('', include(router.urls)),
]
