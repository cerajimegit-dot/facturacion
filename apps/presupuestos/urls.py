"""URLs for presupuestos app."""
from rest_framework.routers import DefaultRouter
from .views import PresupuestoViewSet, PresupuestoDetalleViewSet

router = DefaultRouter()
router.register(r'presupuestos', PresupuestoViewSet, basename='presupuesto')
router.register(r'presupuestos-detalle', PresupuestoDetalleViewSet, basename='presupuesto-detalle')

urlpatterns = router.urls
