"""URL routes for reportes app."""
from django.urls import path
from .views import DashboardView, ReporteVentasView, ReporteCuentasPorCobrarView

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('ventas/', ReporteVentasView.as_view(), name='reporte_ventas'),
    path('cuentas-por-cobrar/', ReporteCuentasPorCobrarView.as_view(), name='reporte_cxc'),
]
