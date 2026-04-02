"""URL routes for contratos app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ContratoViewSet, OrdenServicioViewSet

router = DefaultRouter()
router.register('ordenes-servicio', OrdenServicioViewSet, basename='ordenservicio')
router.register('', ContratoViewSet, basename='contrato')

urlpatterns = [
    path('', include(router.urls)),
]
