"""Dashboard and reporting views."""
import io
from datetime import timedelta
from django.db.models import Sum, Count, F, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from apps.core.mixins import TenantQuerySetMixin
from apps.core.permissions import IsEmpresaMember


class DashboardView(APIView):
    """Main dashboard with KPIs."""
    permission_classes = [IsAuthenticated]

    def get_empresa(self, request):
        empresa_id = request.query_params.get('empresa')
        if not empresa_id:
            return None
        membership = request.user.memberships.filter(
            empresa_id=empresa_id, activo=True
        ).first()
        return membership.empresa if membership else None

    def get(self, request):
        empresa = self.get_empresa(request)
        if not empresa:
            return Response(
                {'detail': 'Parámetro empresa es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.ventas.models import Venta, CuentaPorCobrar
        from apps.clientes.models import Cliente
        from apps.productos.models import Producto
        from apps.pagos.models import Pago

        hoy = timezone.now().date()
        inicio_mes = hoy.replace(day=1)

        # Ventas del mes
        ventas_mes = Venta.objects.filter(
            empresa=empresa, fecha__gte=inicio_mes, fecha__lte=hoy,
        ).exclude(estado='anulada')
        ventas_agg = ventas_mes.aggregate(
            total_ventas=Sum('total'),
            cantidad_ventas=Count('id'),
        )

        # Pagos del mes
        pagos_mes = Pago.objects.filter(
            empresa=empresa, fecha__gte=inicio_mes, fecha__lte=hoy,
            estado='confirmado',
        ).aggregate(total_cobrado=Sum('monto'))

        # Cuentas por cobrar
        cxc = CuentaPorCobrar.objects.filter(empresa=empresa).exclude(
            estado__in=['pagada', 'incobrable']
        )
        cxc_agg = cxc.aggregate(
            total_pendiente=Sum('saldo'),
            cantidad_cxc=Count('id'),
        )
        cxc_vencidas = cxc.filter(fecha_vencimiento__lt=hoy).aggregate(
            total_vencido=Sum('saldo'),
            cantidad_vencidas=Count('id'),
        )

        # Totals
        total_clientes = Cliente.objects.filter(empresa=empresa, activo=True).count()
        total_productos = Producto.objects.filter(empresa=empresa, activo=True).count()

        # Top 5 clients by sales this month
        top_clientes = (
            ventas_mes.values('cliente__nombre')
            .annotate(total=Sum('total'))
            .order_by('-total')[:5]
        )

        return Response({
            'ventas_mes': {
                'total': ventas_agg['total_ventas'] or 0,
                'cantidad': ventas_agg['cantidad_ventas'] or 0,
            },
            'cobros_mes': {
                'total': pagos_mes['total_cobrado'] or 0,
            },
            'cuentas_por_cobrar': {
                'total_pendiente': cxc_agg['total_pendiente'] or 0,
                'cantidad': cxc_agg['cantidad_cxc'] or 0,
                'total_vencido': cxc_vencidas['total_vencido'] or 0,
                'cantidad_vencidas': cxc_vencidas['cantidad_vencidas'] or 0,
            },
            'totales': {
                'clientes_activos': total_clientes,
                'productos_activos': total_productos,
            },
            'top_clientes_mes': list(top_clientes),
            'moneda': empresa.moneda_principal,
        })


class ReporteVentasView(APIView):
    """Sales report with date range and export to Excel."""
    permission_classes = [IsAuthenticated]

    def get_empresa(self, request):
        empresa_id = request.query_params.get('empresa')
        if not empresa_id:
            return None
        membership = request.user.memberships.filter(
            empresa_id=empresa_id, activo=True
        ).first()
        return membership.empresa if membership else None

    def get(self, request):
        empresa = self.get_empresa(request)
        if not empresa:
            return Response(
                {'detail': 'Parámetro empresa es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.ventas.models import Venta

        fecha_desde = request.query_params.get('fecha_desde')
        fecha_hasta = request.query_params.get('fecha_hasta')
        formato = request.query_params.get('formato', 'json')

        qs = Venta.objects.filter(empresa=empresa).exclude(estado='anulada')
        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__lte=fecha_hasta)

        # Summary
        resumen = qs.aggregate(
            total_ventas=Sum('total'),
            total_impuestos=Sum('impuestos'),
            total_cobrado=Sum('total_pagado'),
            total_pendiente=Sum('saldo_pendiente'),
            cantidad=Count('id'),
        )

        # By state
        por_estado = list(
            qs.values('estado')
            .annotate(total=Sum('total'), cantidad=Count('id'))
            .order_by('-total')
        )

        # By month
        from django.db.models.functions import TruncMonth
        por_mes = list(
            qs.annotate(mes=TruncMonth('fecha'))
            .values('mes')
            .annotate(total=Sum('total'), cantidad=Count('id'))
            .order_by('mes')
        )

        if formato == 'excel':
            return self._export_excel(qs, empresa)

        return Response({
            'resumen': resumen,
            'por_estado': por_estado,
            'por_mes': por_mes,
        })

    def _export_excel(self, queryset, empresa):
        import xlsxwriter
        from django.http import HttpResponse

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Ventas')

        headers = ['Número', 'Fecha', 'Cliente', 'Estado', 'Subtotal', 'Impuestos', 'Total', 'Pagado', 'Pendiente']
        bold = workbook.add_format({'bold': True})
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, bold)

        for row, venta in enumerate(queryset.select_related('cliente'), start=1):
            worksheet.write(row, 0, venta.numero)
            worksheet.write(row, 1, str(venta.fecha))
            worksheet.write(row, 2, venta.cliente.nombre)
            worksheet.write(row, 3, venta.estado)
            worksheet.write(row, 4, float(venta.subtotal))
            worksheet.write(row, 5, float(venta.impuestos))
            worksheet.write(row, 6, float(venta.total))
            worksheet.write(row, 7, float(venta.total_pagado))
            worksheet.write(row, 8, float(venta.saldo_pendiente))

        workbook.close()
        output.seek(0)

        response = HttpResponse(
            output.read(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = f'attachment; filename=ventas_{empresa.codigo}.xlsx'
        return response


class ReporteCuentasPorCobrarView(APIView):
    """Accounts receivable aging report."""
    permission_classes = [IsAuthenticated]

    def get_empresa(self, request):
        empresa_id = request.query_params.get('empresa')
        if not empresa_id:
            return None
        membership = request.user.memberships.filter(
            empresa_id=empresa_id, activo=True
        ).first()
        return membership.empresa if membership else None

    def get(self, request):
        empresa = self.get_empresa(request)
        if not empresa:
            return Response(
                {'detail': 'Parámetro empresa es requerido.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.ventas.models import CuentaPorCobrar

        hoy = timezone.now().date()
        qs = CuentaPorCobrar.objects.filter(
            empresa=empresa
        ).exclude(estado__in=['pagada', 'incobrable']).select_related('venta', 'cliente')

        # Aging buckets
        corriente = qs.filter(fecha_vencimiento__gte=hoy)
        vencido_1_30 = qs.filter(
            fecha_vencimiento__lt=hoy,
            fecha_vencimiento__gte=hoy - timedelta(days=30),
        )
        vencido_31_60 = qs.filter(
            fecha_vencimiento__lt=hoy - timedelta(days=30),
            fecha_vencimiento__gte=hoy - timedelta(days=60),
        )
        vencido_61_90 = qs.filter(
            fecha_vencimiento__lt=hoy - timedelta(days=60),
            fecha_vencimiento__gte=hoy - timedelta(days=90),
        )
        vencido_90_plus = qs.filter(
            fecha_vencimiento__lt=hoy - timedelta(days=90),
        )

        def bucket_agg(bucket_qs):
            agg = bucket_qs.aggregate(total=Sum('saldo'), cantidad=Count('id'))
            return {'total': agg['total'] or 0, 'cantidad': agg['cantidad'] or 0}

        # By client
        por_cliente = list(
            qs.values('cliente__nombre')
            .annotate(total_pendiente=Sum('saldo'), cantidad=Count('id'))
            .order_by('-total_pendiente')[:20]
        )

        return Response({
            'corriente': bucket_agg(corriente),
            '1_30_dias': bucket_agg(vencido_1_30),
            '31_60_dias': bucket_agg(vencido_31_60),
            '61_90_dias': bucket_agg(vencido_61_90),
            'mas_90_dias': bucket_agg(vencido_90_plus),
            'por_cliente': por_cliente,
        })
