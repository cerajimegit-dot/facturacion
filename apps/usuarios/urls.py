"""URL routes for authentication and user management."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    EmailLoginView, RegistroView, PerfilView, CambiarPasswordView,
    MembershipViewSet, InvitarUsuarioView,
    ConfiguracionAccesoViewSet, MisPermisosView,
)

router = DefaultRouter()
router.register('memberships', MembershipViewSet, basename='membership')
router.register('config-acceso', ConfiguracionAccesoViewSet, basename='config-acceso')

urlpatterns = [
    path('registro/', RegistroView.as_view(), name='registro'),
    path('login/', EmailLoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('cambiar-password/', CambiarPasswordView.as_view(), name='cambiar_password'),
    path('invitar-usuario/', InvitarUsuarioView.as_view(), name='invitar_usuario'),
    path('mis-permisos/', MisPermisosView.as_view(), name='mis_permisos'),
    path('', include(router.urls)),
]
