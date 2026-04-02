"""Views for Auditoria (read-only)."""
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated
from apps.core.permissions import IsAdministrador
from .models import Auditoria
from .serializers import AuditoriaSerializer


class AuditoriaViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Read-only audit log. Only admins can view."""
    queryset = Auditoria.objects.select_related('usuario', 'empresa')
    serializer_class = AuditoriaSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['accion', 'modelo', 'usuario', 'empresa']
    search_fields = ['descripcion', 'modelo', 'objeto_id']
    ordering_fields = ['timestamp']

    def get_queryset(self):
        qs = super().get_queryset()
        empresa_id = self.request.query_params.get('empresa')
        if empresa_id:
            qs = qs.filter(empresa_id=empresa_id)
        # Only show audit records for empresas the user belongs to
        return qs.filter(
            empresa__memberships__usuario=self.request.user,
            empresa__memberships__activo=True,
        ).distinct()
