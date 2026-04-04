"""URL configuration for facturacion project."""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # API v1
    path('api/v1/auth/', include('apps.usuarios.urls')),
    path('api/v1/empresas/', include('apps.empresas.urls')),
    path('api/v1/clientes/', include('apps.clientes.urls')),
    path('api/v1/productos/', include('apps.productos.urls')),
    path('api/v1/inventario/', include('apps.inventario.urls')),
    path('api/v1/ventas/', include('apps.ventas.urls')),
    path('api/v1/pagos/', include('apps.pagos.urls')),
    path('api/v1/contratos/', include('apps.contratos.urls')),
    path('api/v1/reportes/', include('apps.reportes.urls')),
    path('api/v1/importacion/', include('apps.importacion.urls')),
    path('api/v1/presupuestos/', include('apps.presupuestos.urls')),
    path('api/v1/auditoria/', include('apps.auditoria.urls')),
    path('api/v1/compras/', include('apps.compras.urls')),
    # API Schema
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
