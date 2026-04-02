"""Custom permissions for multi-tenant and role-based access control."""
from rest_framework import permissions


class IsEmpresaMember(permissions.BasePermission):
    """Ensures user belongs to the empresa referenced in the request."""

    def has_permission(self, request, view):
        empresa_id = (
            view.kwargs.get('empresa_pk')
            or request.query_params.get('empresa')
            or (request.data.get('empresa') if hasattr(request, 'data') else None)
        )
        if not empresa_id:
            return True  # Will be filtered in queryset
        return request.user.memberships.filter(
            empresa_id=empresa_id, activo=True
        ).exists()

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'empresa_id'):
            return request.user.memberships.filter(
                empresa_id=obj.empresa_id, activo=True
            ).exists()
        return True


class IsAdministrador(permissions.BasePermission):
    """Only allows Administrador role."""

    def has_permission(self, request, view):
        empresa_id = view.kwargs.get('empresa_pk') or request.query_params.get('empresa')
        if not empresa_id:
            return False
        return request.user.memberships.filter(
            empresa_id=empresa_id, rol='admin', activo=True
        ).exists()


class IsAdminOrReadOnly(permissions.BasePermission):
    """Admin can do anything; others read-only."""

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        empresa_id = view.kwargs.get('empresa_pk') or request.query_params.get('empresa')
        if not empresa_id:
            return False
        return request.user.memberships.filter(
            empresa_id=empresa_id, rol='admin', activo=True
        ).exists()


class IsVendedorOrAbove(permissions.BasePermission):
    """Allows Vendedor, Contador, and Admin roles."""

    def has_permission(self, request, view):
        empresa_id = view.kwargs.get('empresa_pk') or request.query_params.get('empresa')
        if not empresa_id:
            return True
        return request.user.memberships.filter(
            empresa_id=empresa_id,
            rol__in=['admin', 'vendedor', 'contador'],
            activo=True,
        ).exists()
