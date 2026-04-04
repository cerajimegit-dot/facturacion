"""View mixins for multi-tenant filtering."""
from rest_framework.exceptions import ValidationError


class TenantQuerySetMixin:
    """Mixin that filters querysets by the empresa from request context."""

    def get_empresa(self):
        empresa_id = (
            self.kwargs.get('empresa_pk')
            or self.request.query_params.get('empresa')
        )
        if not empresa_id:
            raise ValidationError({'empresa': 'Este parámetro es requerido.'})
        
        # Check membership via Membership model
        membership = self.request.user.memberships.filter(
            empresa_id=empresa_id, activo=True
        ).first()
        
        # Fallback: Check if user's direct empresa matches
        if not membership and self.request.user.empresa_id == empresa_id:
            # Create membership if it doesn't exist (backward compatibility)
            from apps.usuarios.models import Membership
            membership, _ = Membership.objects.get_or_create(
                usuario=self.request.user,
                empresa_id=empresa_id,
                defaults={'rol': self.request.user.rol, 'activo': True}
            )
        
        if not membership:
            raise ValidationError({'empresa': 'No tiene acceso a esta empresa.'})
        return membership.empresa

    def get_queryset(self):
        qs = super().get_queryset()
        empresa = self.get_empresa()
        return qs.filter(empresa=empresa)

    def perform_create(self, serializer):
        empresa = self.get_empresa()
        serializer.save(empresa=empresa)
