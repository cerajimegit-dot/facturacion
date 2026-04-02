"""URL routes for productos app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductoViewSet, CategoriaViewSet, PrecioListaViewSet

router = DefaultRouter()
router.register('categorias', CategoriaViewSet, basename='categoria')
router.register('precios', PrecioListaViewSet, basename='preciolista')
router.register('', ProductoViewSet, basename='producto')

urlpatterns = [
    path('', include(router.urls)),
]
