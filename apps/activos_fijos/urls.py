"""URL routes para el modulo de Activos Fijos."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClasificacionActivoViewSet, UbicacionActivoViewSet, CentroCostoViewSet,
    ActivoFijoViewSet, MovimientoActivoViewSet, MantenimientoActivoViewSet,
    BajaActivoViewSet, DepreciacionMensualViewSet,
)

router = DefaultRouter()
router.register('clasificaciones', ClasificacionActivoViewSet, basename='clasificacion-activo')
router.register('ubicaciones', UbicacionActivoViewSet, basename='ubicacion-activo')
router.register('centros-costo', CentroCostoViewSet, basename='centro-costo')
router.register('movimientos', MovimientoActivoViewSet, basename='movimiento-activo')
router.register('mantenimientos', MantenimientoActivoViewSet, basename='mantenimiento-activo')
router.register('bajas', BajaActivoViewSet, basename='baja-activo')
router.register('depreciaciones', DepreciacionMensualViewSet, basename='depreciacion')
router.register('activos', ActivoFijoViewSet, basename='activo-fijo')

urlpatterns = [
    path('', include(router.urls)),
]
