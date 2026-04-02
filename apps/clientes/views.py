"""Views for Cliente management."""
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from apps.core.mixins import TenantQuerySetMixin
from apps.core.permissions import IsEmpresaMember
from .models import Cliente, DireccionCliente, ContactoCliente
from .serializers import (
    ClienteSerializer,
    ClienteListSerializer,
    DireccionClienteSerializer,
    ContactoClienteSerializer,
)


class ClienteViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    """CRUD for clients, scoped by empresa."""
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['tipo_cliente', 'activo', 'sector', 'zona']
    search_fields = ['nombre', 'ruc', 'email', 'telefono']
    ordering_fields = ['nombre', 'created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ClienteListSerializer
        return ClienteSerializer

    @action(detail=True, methods=['get', 'post'])
    def direcciones(self, request, pk=None):
        cliente = self.get_object()
        if request.method == 'POST':
            serializer = DireccionClienteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(cliente=cliente)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        serializer = DireccionClienteSerializer(cliente.direcciones.all(), many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def contactos(self, request, pk=None):
        cliente = self.get_object()
        if request.method == 'POST':
            serializer = ContactoClienteSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save(cliente=cliente)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        serializer = ContactoClienteSerializer(cliente.contactos.all(), many=True)
        return Response(serializer.data)
