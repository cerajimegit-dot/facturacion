"""Vistas para el módulo de contabilidad."""
import re
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd

from apps.contabilidad.models import (
    PlanCuentas, Asiento, LineaAsiento, CotizacionDiaria, SaldoCuenta
)
from apps.contabilidad.serializers import (
    PlanCuentasSerializer, PlanCuentasListSerializer,
    AsientoDetailedSerializer, AsientoListSerializer, AsientoCrearSerializer,
    LineaAsientoSerializer, CotizacionDiariaSerializer, SaldoCuentaSerializer,
    BalanceGeneralSerializer
)
from apps.core.permissions import IsEmpresaMember


class PlanCuentasViewSet(viewsets.ModelViewSet):
    """ViewSet para plan de cuentas."""
    
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    queryset = PlanCuentas.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PlanCuentasListSerializer
        return PlanCuentasSerializer
    
    def get_queryset(self):
        usuario = self.request.user
        return PlanCuentas.objects.filter(
            empresa=usuario.empresa,
            activa=True
        ).order_by('codigo_cuenta')
    
    def perform_create(self, serializer):
        serializer.save(empresa=self.request.user.empresa)
    
    @action(detail=False, methods=['get'])
    def por_condicion(self, request):
        """Obtener cuentas agrupadas por condición."""
        condicion = request.query_params.get('condicion')
        
        if not condicion:
            return Response(
                {'error': 'Parámetro "condicion" requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        cuentas = self.get_queryset().filter(condicion=condicion)
        serializer = PlanCuentasListSerializer(cuentas, many=True)
        
        return Response({
            'condicion': condicion,
            'total': cuentas.count(),
            'cuentas': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def arbol(self, request):
        """Obtener árbol de cuentas (sintéticas y analíticas)."""
        cuentas_sinteticas = self.get_queryset().filter(
            clase='sintetica',
            parent__isnull=True
        )
        
        data = []
        for cuenta in cuentas_sinteticas:
            data.append({
                'cuenta': PlanCuentasSerializer(cuenta).data,
                'subcuentas': PlanCuentasListSerializer(
                    cuenta.subcuentas.filter(activa=True),
                    many=True
                ).data
            })
        
        return Response(data)

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def importar(self, request):
        """Importar plan de cuentas desde archivo Excel formato ANEXO 1."""
        archivo = request.FILES.get('archivo')
        if not archivo:
            return Response(
                {'error': 'Se requiere un archivo Excel'},
                status=status.HTTP_400_BAD_REQUEST
            )

        allowed_ext = ('.xlsx', '.xls')
        if not archivo.name.lower().endswith(allowed_ext):
            return Response(
                {'error': 'Solo se aceptan archivos .xlsx o .xls'},
                status=status.HTTP_400_BAD_REQUEST
            )

        empresa = request.user.empresa
        code_pattern = re.compile(r'^\d[\d.]*$')

        try:
            df = pd.read_excel(archivo, header=None)
        except Exception as e:
            return Response(
                {'error': f'No se pudo leer el archivo: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Parse accounts from ANEXO 1 format
        accounts = []
        for _, row in df.iterrows():
            raw_code = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ''
            raw_desc = str(row.iloc[1]).strip() if pd.notna(row.iloc[1]) else ''
            if not raw_code or not raw_desc:
                continue
            if not code_pattern.match(raw_code):
                continue
            if 'xx' in raw_code:
                continue
            accounts.append((raw_code, raw_desc))

        if not accounts:
            return Response(
                {'error': 'No se encontraron cuentas válidas en el archivo'},
                status=status.HTTP_400_BAD_REQUEST
            )

        preview = request.query_params.get('preview', 'false').lower() == 'true'
        if preview:
            preview_data = []
            for cod, desc in accounts:
                exists = PlanCuentas.objects.filter(empresa=empresa, codigo_cuenta=cod).exists()
                preview_data.append({
                    'codigo_cuenta': cod,
                    'descripcion': desc,
                    'existe': exists,
                })
            return Response({
                'total': len(preview_data),
                'nuevas': sum(1 for p in preview_data if not p['existe']),
                'existentes': sum(1 for p in preview_data if p['existe']),
                'cuentas': preview_data,
            })

        # Actual import
        created = 0
        updated = 0
        for cod, desc in accounts:
            parts = cod.split('.')
            condicion = 'deudora' if cod.startswith('1') else 'acreedora'
            clase = 'sintetica' if len(parts) <= 3 else 'analitica'

            _, was_created = PlanCuentas.objects.update_or_create(
                empresa=empresa,
                codigo_cuenta=cod,
                defaults={
                    'descripcion': desc,
                    'condicion': condicion,
                    'clase': clase,
                    'activa': True,
                }
            )
            if was_created:
                created += 1
            else:
                updated += 1

        # Set parent relationships
        parents_set = 0
        for cod, _ in accounts:
            parent_parts = cod.split('.')
            if len(parent_parts) <= 1:
                continue
            parent_code = '.'.join(parent_parts[:-1])
            parent = PlanCuentas.objects.filter(empresa=empresa, codigo_cuenta=parent_code).first()
            if parent:
                PlanCuentas.objects.filter(empresa=empresa, codigo_cuenta=cod).update(parent=parent)
                parents_set += 1

        total = PlanCuentas.objects.filter(empresa=empresa).count()
        return Response({
            'creadas': created,
            'actualizadas': updated,
            'parentescos': parents_set,
            'total_en_bd': total,
        })


class AsientoViewSet(viewsets.ModelViewSet):
    """ViewSet para asientos contables."""
    
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    queryset = Asiento.objects.all()
    
    def get_serializer_class(self):
        if self.action == 'list':
            return AsientoListSerializer
        elif self.action == 'create':
            return AsientoCrearSerializer
        return AsientoDetailedSerializer
    
    def get_queryset(self):
        usuario = self.request.user
        return Asiento.objects.filter(
            empresa=usuario.empresa
        ).order_by('-fecha', '-numero_asiento')
    
    def perform_create(self, serializer):
        serializer.save(
            empresa=self.request.user.empresa,
            usuario_crea=self.request.user
        )
    
    @action(detail=True, methods=['post'])
    def registrar(self, request, pk=None):
        """Registrar un asiento contable."""
        asiento = self.get_object()
        
        if asiento.estado != 'borrador':
            return Response(
                {'error': 'Solo se pueden registrar asientos en borrador'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            asiento.registrar(request.user)
            serializer = self.get_serializer(asiento)
            return Response(serializer.data)
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def reversar(self, request, pk=None):
        """Reversar un asiento contable."""
        asiento = self.get_object()
        
        if asiento.estado != 'registrado':
            return Response(
                {'error': 'Solo se pueden reversar asientos registrados'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear asiento de reversa
        reversa = Asiento.objects.create(
            empresa=asiento.empresa,
            numero_asiento=f"{asiento.numero_asiento}R",
            tipo_asiento=f"{asiento.tipo_asiento}_REVERSA",
            fecha=timezone.now().date(),
            descripcion=f"Reversa de {asiento.numero_asiento}",
            moneda=asiento.moneda,
            estado='registrado',
            usuario_crea=request.user,
        )
        
        # Copiar líneas invertidas
        for linea in asiento.lineas.all():
            LineaAsiento.objects.create(
                asiento=reversa,
                empresa=asiento.empresa,
                cuenta=linea.cuenta,
                debe=linea.haber,
                haber=linea.debe,
                observacion=f"Reversa: {linea.observacion}",
                item_contable=linea.item_contable,
            )
        
        reversa.total_debe = asiento.total_haber
        reversa.total_haber = asiento.total_debe
        reversa.save()
        
        # Marcar original como reversado
        asiento.estado = 'reversado'
        asiento.save()
        
        serializer = self.get_serializer(reversa)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['get'])
    def por_tipo(self, request):
        """Obtener asientos por tipo."""
        tipo = request.query_params.get('tipo')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        
        queryset = self.get_queryset()
        
        if tipo:
            queryset = queryset.filter(tipo_asiento=tipo)
        
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'total': queryset.count(),
            'asientos': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def balance_general(self, request):
        """Generar balance general."""
        fecha = request.query_params.get('fecha', timezone.now().date())
        
        asientos = self.get_queryset().filter(
            fecha__lte=fecha,
            estado='registrado'
        )
        
        activos = Decimal('0')
        pasivos = Decimal('0')
        patrimonio = Decimal('0')
        
        for asiento in asientos:
            for linea in asiento.lineas.all():
                neto = linea.debe - linea.haber
                
                if linea.cuenta.condicion == 'deudora':
                    activos += neto
                else:
                    pasivos -= neto
        
        # Patrimonio = Activos - Pasivos
        patrimonio = activos - pasivos
        
        return Response({
            'fecha': fecha,
            'activos': str(activos),
            'pasivos': str(pasivos),
            'patrimonio': str(patrimonio),
            'balanceado': activos == pasivos + patrimonio
        })


class CotizacionDiariaViewSet(viewsets.ModelViewSet):
    """ViewSet para cotizaciones diarias."""
    
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    
    def get_queryset(self):
        usuario = self.request.user
        return CotizacionDiaria.objects.filter(
            empresa=usuario.empresa
        ).order_by('-fecha')
    
    def get_serializer_class(self):
        return CotizacionDiariaSerializer
    
    def perform_create(self, serializer):
        serializer.save(
            empresa=self.request.user.empresa,
            usuario_carga=self.request.user
        )
    
    @action(detail=False, methods=['get'])
    def hoy(self, request):
        """Obtener cotización del día (o de una fecha específica)."""
        fecha_param = request.query_params.get('fecha')
        if fecha_param:
            try:
                hoy = datetime.strptime(fecha_param, '%Y-%m-%d').date()
            except ValueError:
                hoy = timezone.now().date()
        else:
            hoy = timezone.now().date()
        
        cotizacion = CotizacionDiaria.objects.filter(
            empresa=request.user.empresa,
            fecha=hoy
        ).first()
        
        if not cotizacion:
            return Response(
                {'error': f'No hay cotización para {hoy}'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(cotizacion)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def rango(self, request):
        """Obtener cotizaciones en un rango de fechas."""
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        
        queryset = self.get_queryset()
        
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'total': queryset.count(),
            'cotizaciones': serializer.data
        })


class SaldoCuentaViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet de solo lectura para saldos de cuenta."""
    
    permission_classes = [IsAuthenticated, IsEmpresaMember]
    serializer_class = SaldoCuentaSerializer
    
    def get_queryset(self):
        usuario = self.request.user
        return SaldoCuenta.objects.filter(
            empresa=usuario.empresa
        ).order_by('cuenta', '-fecha')
    
    @action(detail=False, methods=['get'])
    def por_cuenta(self, request):
        """Obtener saldos por cuenta."""
        cuenta_id = request.query_params.get('cuenta_id')
        fecha = request.query_params.get('fecha')
        
        queryset = self.get_queryset()
        
        if cuenta_id:
            queryset = queryset.filter(cuenta_id=cuenta_id)
        if fecha:
            queryset = queryset.filter(fecha__lte=fecha)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'total': queryset.count(),
            'saldos': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def por_fecha(self, request):
        """Obtener saldos por fecha."""
        fecha = request.query_params.get('fecha')
        
        if not fecha:
            return Response(
                {'error': 'Parámetro "fecha" requerido'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(fecha=fecha)
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'fecha': fecha,
            'total_cuentas': queryset.count(),
            'saldos': serializer.data
        })
