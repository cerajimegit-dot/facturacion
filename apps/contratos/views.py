"""Views for Contrato and OrdenServicio."""
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from apps.core.mixins import TenantQuerySetMixin
from apps.core.permissions import IsEmpresaMember
from .models import Contrato, OrdenServicio
from .serializers import ContratoSerializer, OrdenServicioSerializer


class ContratoViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = Contrato.objects.select_related('cliente')
    serializer_class = ContratoSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['estado', 'cliente', 'frecuencia_cobro']
    search_fields = ['numero', 'cliente__nombre', 'descripcion']
    ordering_fields = ['fecha_inicio', 'numero']


class OrdenServicioViewSet(TenantQuerySetMixin, viewsets.ModelViewSet):
    queryset = OrdenServicio.objects.select_related('cliente', 'contrato', 'asignado_a')
    serializer_class = OrdenServicioSerializer
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    filterset_fields = ['estado', 'prioridad', 'cliente', 'contrato', 'asignado_a']
    search_fields = ['numero', 'cliente__nombre', 'descripcion']
    ordering_fields = ['fecha_programada', 'prioridad', 'created_at']
