"""Views for Empresa management."""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Empresa
from .serializers import EmpresaSerializer, EmpresaListSerializer


class EmpresaViewSet(viewsets.ModelViewSet):
    """CRUD for empresas. Users only see empresas they belong to."""
    serializer_class = EmpresaSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Empresa.objects.filter(
            memberships__usuario=self.request.user,
            memberships__activo=True,
        ).distinct()

    def get_serializer_class(self):
        if self.action == 'list':
            return EmpresaListSerializer
        return EmpresaSerializer

    def perform_create(self, serializer):
        from apps.usuarios.models import Membership
        empresa = serializer.save()
        Membership.objects.create(
            usuario=self.request.user,
            empresa=empresa,
            rol='admin',
        )
