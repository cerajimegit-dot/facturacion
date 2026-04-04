"""Views for presupuestos app."""
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Presupuesto, PresupuestoDetalle
from .serializers import (
    PresupuestoSerializer, PresupuestoCreateUpdateSerializer,
    PresupuestoDetalleSerializer
)
from .tasks import enviar_presupuesto_email, enviar_presupuesto_whatsapp

logger = logging.getLogger(__name__)


class PresupuestoViewSet(viewsets.ModelViewSet):
    """ViewSet for Presupuesto management."""
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'cliente', 'fecha_creacion']
    search_fields = ['numero', 'cliente__nombre']
    ordering_fields = ['fecha_creacion', 'numero', 'total']
    ordering = ['-fecha_creacion']
    
    def get_queryset(self):
        """Filter by empresa from user membership."""
        user = self.request.user
        empresas = user.memberships.filter(
            activo=True
        ).values_list('empresa_id', flat=True)
        return Presupuesto.objects.filter(empresa_id__in=empresas).select_related(
            'cliente', 'creado_por'
        ).prefetch_related('detalles')
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PresupuestoCreateUpdateSerializer
        return PresupuestoSerializer
    
    def perform_create(self, serializer):
        """Automatically set empresa and user."""
        user = self.request.user
        empresa = user.memberships.filter(activo=True).first()
        if not empresa:
            return Response(
                {'detail': 'No tiene acceso a ninguna empresa.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer.save(empresa_id=empresa.empresa_id, creado_por=user)
    
    @action(detail=True, methods=['post'])
    def enviar_email(self, request, pk=None):
        """Send presupuesto via email."""
        presupuesto = self.get_object()
        
        if not presupuesto.email_cliente:
            return Response(
                {'detail': 'No hay email del cliente registrado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            enviar_presupuesto_email(presupuesto.id)
            presupuesto.estado = 'enviado'
            presupuesto.save()
            return Response({'detail': 'Presupuesto enviado por email.'})
        except Exception as e:
            logger.exception(f"Error enviando presupuesto {presupuesto.id} por email: {e}")
            return Response(
                {'detail': f'Error al enviar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    
    @action(detail=True, methods=['post'])
    def enviar_whatsapp(self, request, pk=None):
        """Send presupuesto via WhatsApp."""
        presupuesto = self.get_object()
        
        if not presupuesto.telefono_cliente:
            return Response(
                {'detail': 'No hay teléfono del cliente registrado.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        try:
            enviar_presupuesto_whatsapp(presupuesto.id)
            presupuesto.estado = 'enviado'
            presupuesto.save()
            return Response({'detail': 'Presupuesto enviado por WhatsApp.'})
        except Exception as e:
            logger.exception(f"Error enviando presupuesto {presupuesto.id} por WhatsApp: {e}")
            return Response(
                {'detail': f'Error al enviar: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Generate and download presupuesto as PDF."""
        presupuesto = self.get_object()
        # TODO: Implement PDF generation
        return Response({'detail': 'PDF generation not implemented yet.'})


class PresupuestoDetalleViewSet(viewsets.ModelViewSet):
    """ViewSet for PresupuestoDetalle items."""
    permission_classes = [IsAuthenticated]
    serializer_class = PresupuestoDetalleSerializer
    
    def get_queryset(self):
        """Filter by presupuesto."""
        presupuesto_id = self.request.query_params.get('presupuesto_id')
        if presupuesto_id:
            return PresupuestoDetalle.objects.filter(presupuesto_id=presupuesto_id)
        return PresupuestoDetalle.objects.none()
    
    def perform_create(self, serializer):
        """Calculate totals after creating."""
        detalle = serializer.save()
        detalle.calcular_totales()
    
    def perform_update(self, serializer):
        """Calculate totals after updating."""
        detalle = serializer.save()
        detalle.calcular_totales()
