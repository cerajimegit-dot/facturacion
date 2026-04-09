"""Tests for audit improvements:
- Auto accounting entries on sale confirmation
- Stock deduction on sale confirmation
- IVA rate restriction (10%, 5%, 0%)
- Credit limit validation
- Block editing confirmed sales
- CxC anulación state fix
- Notas de Crédito
- RUC validation
- Aging report
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.urls import reverse
from rest_framework import status
from apps.clientes.models import Cliente, validar_ruc_paraguayo
from apps.productos.models import Producto
from apps.ventas.models import (
    Venta, LineaVenta, CuentaPorCobrar, NotaCredito, LineaNotaCredito,
    CONDICION_IVA_CHOICES, IVA_TASA_MAP,
)
from apps.pagos.models import Pago
from apps.contabilidad.models import PlanCuentas, Asiento, LineaAsiento
from apps.inventario.models import Almacen, Stock, MovimientoStock
from apps.ventas.services import VentaService, PagoService
from django.core.exceptions import ValidationError


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def cliente_test(empresa_context):
    _, empresa = empresa_context
    return Cliente.objects.create(
        empresa=empresa, nombre='Cliente Audit', ruc='80012345-0',
        limite_credito=Decimal('500000'),
    )


@pytest.fixture
def cliente_sin_limite(empresa_context):
    _, empresa = empresa_context
    return Cliente.objects.create(
        empresa=empresa, nombre='Cliente Sin Limite', ruc='4839399-1',
        limite_credito=Decimal('0'),
    )


@pytest.fixture
def producto_test(empresa_context):
    _, empresa = empresa_context
    return Producto.objects.create(
        empresa=empresa, sku='PROD-AUD01', nombre='Producto Audit Test',
        precio_unitario=Decimal('100000'), impuesto_porcentaje=Decimal('10'),
        tipo='producto',
    )


@pytest.fixture
def almacen_test(empresa_context):
    _, empresa = empresa_context
    return Almacen.objects.create(
        empresa=empresa, codigo='ALM01', nombre='Almacén Principal',
    )


@pytest.fixture
def stock_test(empresa_context, producto_test, almacen_test):
    _, empresa = empresa_context
    return Stock.objects.create(
        empresa=empresa, producto=producto_test, almacen=almacen_test,
        cantidad=Decimal('100'), stock_minimo=Decimal('10'),
    )


@pytest.fixture
def plan_cuentas(empresa_context):
    """Create minimal chart of accounts for testing."""
    _, empresa = empresa_context
    cuentas = {}
    datos = [
        ('1130', 'Cuentas por Cobrar', 'deudora'),
        ('4110', 'Ingresos por Ventas', 'acreedora'),
        ('2120', 'IVA Débito Fiscal', 'acreedora'),
        ('1110', 'Caja', 'deudora'),
        ('1120', 'Bancos', 'deudora'),
        ('1410', 'Mercaderías', 'deudora'),
        ('1510', 'IVA Crédito Fiscal', 'deudora'),
        ('2110', 'Cuentas por Pagar', 'acreedora'),
        ('4120', 'Devoluciones sobre Ventas', 'deudora'),
    ]
    for codigo, desc, condicion in datos:
        cuentas[codigo] = PlanCuentas.objects.create(
            empresa=empresa,
            codigo_cuenta=codigo,
            descripcion=desc,
            condicion=condicion,
            clase='analitica',
            activa=True,
        )
    return cuentas


@pytest.fixture
def venta_borrador(empresa_context, cliente_test, producto_test, stock_test):
    """Create a draft venta with one line."""
    _, empresa = empresa_context
    venta = Venta.objects.create(
        empresa=empresa, numero='V-AUD-001',
        cliente=cliente_test, fecha=date.today(),
        estado='borrador',
    )
    linea = LineaVenta(
        venta=venta, empresa=empresa, producto=producto_test,
        cantidad=Decimal('2'), precio_unitario=Decimal('100000'),
        condicion_iva='gravada_10',
    )
    linea.save()
    venta.recalcular_totales()
    return venta


# ═══════════════════════════════════════════════════════════════════════════════
# 1. IVA Rate Restriction Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestIVARateRestriction:
    """IVA must be restricted to 10%, 5%, or 0% (exenta)."""

    def test_condicion_iva_gravada_10(self, empresa_context, producto_test):
        _, empresa = empresa_context
        venta = Venta.objects.create(
            empresa=empresa, numero='V-IVA10',
            cliente=Cliente.objects.create(empresa=empresa, nombre='IVA10', ruc='1234567-8'),
            fecha=date.today(),
        )
        linea = LineaVenta(
            venta=venta, empresa=empresa, producto=producto_test,
            cantidad=Decimal('1'), precio_unitario=Decimal('100000'),
            condicion_iva='gravada_10',
        )
        linea.save()
        assert linea.impuesto_porcentaje == Decimal('10')
        assert linea.impuesto_monto == Decimal('10000')

    def test_condicion_iva_gravada_5(self, empresa_context, producto_test):
        _, empresa = empresa_context
        venta = Venta.objects.create(
            empresa=empresa, numero='V-IVA5',
            cliente=Cliente.objects.create(empresa=empresa, nombre='IVA5', ruc='2345678-9'),
            fecha=date.today(),
        )
        linea = LineaVenta(
            venta=venta, empresa=empresa, producto=producto_test,
            cantidad=Decimal('1'), precio_unitario=Decimal('100000'),
            condicion_iva='gravada_5',
        )
        linea.save()
        assert linea.impuesto_porcentaje == Decimal('5')
        assert linea.impuesto_monto == Decimal('5000')

    def test_condicion_iva_exenta(self, empresa_context, producto_test):
        _, empresa = empresa_context
        venta = Venta.objects.create(
            empresa=empresa, numero='V-IVAE',
            cliente=Cliente.objects.create(empresa=empresa, nombre='IVAE', ruc='3456789-0'),
            fecha=date.today(),
        )
        linea = LineaVenta(
            venta=venta, empresa=empresa, producto=producto_test,
            cantidad=Decimal('1'), precio_unitario=Decimal('100000'),
            condicion_iva='exenta',
        )
        linea.save()
        assert linea.impuesto_porcentaje == Decimal('0')
        assert linea.impuesto_monto == Decimal('0')
        assert linea.total == Decimal('100000')

    def test_iva_forced_from_condicion(self, empresa_context, producto_test):
        """Even if impuesto_porcentaje is set differently, condicion_iva overrides."""
        _, empresa = empresa_context
        venta = Venta.objects.create(
            empresa=empresa, numero='V-FORCED',
            cliente=Cliente.objects.create(empresa=empresa, nombre='Forced', ruc='5679012-3'),
            fecha=date.today(),
        )
        linea = LineaVenta(
            venta=venta, empresa=empresa, producto=producto_test,
            cantidad=Decimal('1'), precio_unitario=Decimal('100000'),
            condicion_iva='gravada_5',
            impuesto_porcentaje=Decimal('7.5'),  # Should be overridden
        )
        linea.save()
        assert linea.impuesto_porcentaje == Decimal('5')  # Forced to legal rate


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Auto Accounting Entry Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAutoAccountingEntries:
    """Accounting entries generated automatically on confirm."""

    def test_asiento_generado_al_confirmar_venta(self, empresa_context, venta_borrador, plan_cuentas):
        _, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        # Check asiento was created
        asiento = Asiento.objects.filter(venta=venta_borrador).first()
        assert asiento is not None
        assert asiento.tipo_asiento == 'VENTA'
        assert asiento.estado == 'registrado'
        assert asiento.total_debe == asiento.total_haber  # Balanced
        assert asiento.total_debe == venta_borrador.total

        # Check lines
        lineas = asiento.lineas.all()
        assert lineas.count() == 3  # CxC Debit, Ingresos Credit, IVA DF Credit

        debitos = sum(l.debe for l in lineas)
        creditos = sum(l.haber for l in lineas)
        assert debitos == creditos

    def test_asiento_pago_generado(self, empresa_context, venta_borrador, plan_cuentas, cliente_test):
        _, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        pago = Pago.objects.create(
            empresa=empresa, venta=venta_borrador,
            cliente=cliente_test, fecha=date.today(),
            monto=venta_borrador.total, metodo='efectivo',
        )
        PagoService.confirmar_pago(pago)

        # Count asientos: 1 for venta + 1 for pago
        asientos = Asiento.objects.filter(empresa=empresa)
        assert asientos.count() == 2

        asiento_pago = asientos.filter(tipo_asiento='PAGO').first()
        assert asiento_pago is not None
        assert asiento_pago.total_debe == pago.monto

    def test_no_asiento_sin_plan_cuentas(self, empresa_context, venta_borrador):
        """If no chart of accounts, sale still confirms but no asiento."""
        _, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        assert venta_borrador.estado == 'confirmada'
        asiento = Asiento.objects.filter(venta=venta_borrador).first()
        assert asiento is None  # Gracefully omitted


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Stock Deduction Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestStockDeduction:
    """Stock is deducted when sale is confirmed."""

    def test_stock_descontado_al_confirmar(self, empresa_context, venta_borrador, stock_test):
        _, empresa = empresa_context
        stock_antes = stock_test.cantidad  # 100

        VentaService.confirmar_venta(venta_borrador)

        stock_test.refresh_from_db()
        assert stock_test.cantidad == stock_antes - Decimal('2')  # 2 units sold

    def test_movimiento_stock_creado(self, empresa_context, venta_borrador, stock_test):
        _, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        movimientos = MovimientoStock.objects.filter(
            empresa=empresa, tipo='salida',
        )
        assert movimientos.count() == 1
        assert movimientos.first().cantidad == Decimal('2')

    def test_error_stock_insuficiente(self, empresa_context, cliente_sin_limite, producto_test, stock_test):
        _, empresa = empresa_context
        # Use more than available
        venta = Venta.objects.create(
            empresa=empresa, numero='V-NOSTOCK',
            cliente=cliente_sin_limite, fecha=date.today(),
        )
        linea = LineaVenta(
            venta=venta, empresa=empresa, producto=producto_test,
            cantidad=Decimal('200'),  # More than 100 available
            precio_unitario=Decimal('100000'),
            condicion_iva='gravada_10',
        )
        linea.save()
        venta.recalcular_totales()

        with pytest.raises(ValueError, match='Stock insuficiente'):
            VentaService.confirmar_venta(venta)

    def test_stock_revertido_al_anular(self, empresa_context, venta_borrador, stock_test):
        _, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        stock_test.refresh_from_db()
        stock_despues_venta = stock_test.cantidad

        VentaService.anular_venta(venta_borrador)

        stock_test.refresh_from_db()
        assert stock_test.cantidad == stock_despues_venta + Decimal('2')


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Credit Limit Validation Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCreditLimit:
    """Credit limit validation on sale confirmation."""

    def test_limite_credito_excedido(self, empresa_context, producto_test, stock_test):
        _, empresa = empresa_context
        cliente = Cliente.objects.create(
            empresa=empresa, nombre='Limite Bajo', ruc='6789012-3',
            limite_credito=Decimal('100000'),
        )
        venta = Venta.objects.create(
            empresa=empresa, numero='V-LIMIT',
            cliente=cliente, fecha=date.today(),
        )
        linea = LineaVenta(
            venta=venta, empresa=empresa, producto=producto_test,
            cantidad=Decimal('5'), precio_unitario=Decimal('100000'),
            condicion_iva='gravada_10',
        )
        linea.save()
        venta.recalcular_totales()
        # Total = 5 * 100000 + 10% = 550000, limit = 100000

        with pytest.raises(ValueError, match='Límite de crédito excedido'):
            VentaService.confirmar_venta(venta)

    def test_sin_limite_credito_permite(self, empresa_context, cliente_sin_limite, producto_test, stock_test):
        _, empresa = empresa_context
        venta = Venta.objects.create(
            empresa=empresa, numero='V-NOLIMIT',
            cliente=cliente_sin_limite, fecha=date.today(),
        )
        linea = LineaVenta(
            venta=venta, empresa=empresa, producto=producto_test,
            cantidad=Decimal('2'), precio_unitario=Decimal('100000'),
            condicion_iva='gravada_10',
        )
        linea.save()
        venta.recalcular_totales()

        # Should not raise (limit is 0 = unlimited)
        VentaService.confirmar_venta(venta)
        assert venta.estado == 'confirmada'


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Block Editing Confirmed Sales Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestBlockEditConfirmed:
    """Confirmed sales cannot be edited via API."""

    def test_no_editar_venta_confirmada(self, empresa_context, venta_borrador, stock_test):
        client, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        url = reverse('venta-detail', kwargs={'pk': str(venta_borrador.id)})
        response = client.put(
            f"{url}?empresa={empresa.id}",
            {'numero': 'HACKED', 'cliente': str(venta_borrador.cliente.id), 'fecha': '2025-01-01'},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_editar_observaciones_cobro_permitido(self, empresa_context, venta_borrador, stock_test):
        client, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        url = reverse('venta-detail', kwargs={'pk': str(venta_borrador.id)})
        response = client.patch(
            f"{url}?empresa={empresa.id}",
            {'observaciones_cobro': 'Seguimiento OK'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK

    def test_no_eliminar_venta_confirmada(self, empresa_context, venta_borrador, stock_test):
        client, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        url = reverse('venta-detail', kwargs={'pk': str(venta_borrador.id)})
        response = client.delete(f"{url}?empresa={empresa.id}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


# ═══════════════════════════════════════════════════════════════════════════════
# 6. CxC Anulación State Fix
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestCxCAnulacion:
    """CxC should be 'anulada' not 'pagada' when sale is voided."""

    def test_cxc_anulada_no_pagada(self, empresa_context, venta_borrador, stock_test):
        _, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        cxc = CuentaPorCobrar.objects.filter(venta=venta_borrador).first()
        assert cxc is not None

        VentaService.anular_venta(venta_borrador)

        cxc.refresh_from_db()
        assert cxc.estado == 'anulada'  # NOT 'pagada'
        assert cxc.saldo == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Nota de Crédito Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestNotaCredito:
    """Nota de Crédito for partial adjustments."""

    def test_crear_y_confirmar_nota_credito(self, empresa_context, venta_borrador, stock_test, plan_cuentas, producto_test):
        _, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        total_original = venta_borrador.total

        # Create NC
        nc = NotaCredito.objects.create(
            empresa=empresa, numero='NC-001',
            venta_original=venta_borrador,
            cliente=venta_borrador.cliente,
            fecha=date.today(), motivo='devolucion',
        )
        linea = LineaNotaCredito(
            nota_credito=nc, empresa=empresa, producto=producto_test,
            cantidad=Decimal('1'), precio_unitario=Decimal('100000'),
            condicion_iva='gravada_10',
        )
        linea.save()
        nc.recalcular_totales()

        VentaService.confirmar_nota_credito(nc)

        assert nc.estado == 'confirmada'

        # Venta saldo adjusted
        venta_borrador.refresh_from_db()
        assert venta_borrador.total_pagado == nc.total
        assert venta_borrador.saldo_pendiente == total_original - nc.total

    def test_nc_devuelve_stock(self, empresa_context, venta_borrador, stock_test, producto_test):
        _, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        stock_test.refresh_from_db()
        stock_post_venta = stock_test.cantidad

        nc = NotaCredito.objects.create(
            empresa=empresa, numero='NC-002',
            venta_original=venta_borrador,
            cliente=venta_borrador.cliente,
            fecha=date.today(), motivo='devolucion',
        )
        linea = LineaNotaCredito(
            nota_credito=nc, empresa=empresa, producto=producto_test,
            cantidad=Decimal('1'), precio_unitario=Decimal('100000'),
            condicion_iva='gravada_10',
        )
        linea.save()
        nc.recalcular_totales()
        VentaService.confirmar_nota_credito(nc)

        stock_test.refresh_from_db()
        assert stock_test.cantidad == stock_post_venta + Decimal('1')

    def test_nc_genera_asiento(self, empresa_context, venta_borrador, stock_test, plan_cuentas, producto_test):
        _, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        nc = NotaCredito.objects.create(
            empresa=empresa, numero='NC-003',
            venta_original=venta_borrador,
            cliente=venta_borrador.cliente,
            fecha=date.today(), motivo='descuento',
        )
        linea = LineaNotaCredito(
            nota_credito=nc, empresa=empresa, producto=producto_test,
            cantidad=Decimal('1'), precio_unitario=Decimal('50000'),
            condicion_iva='gravada_10',
        )
        linea.save()
        nc.recalcular_totales()
        VentaService.confirmar_nota_credito(nc)

        asiento_nc = Asiento.objects.filter(tipo_asiento='NOTA_CREDITO').first()
        assert asiento_nc is not None
        assert asiento_nc.total_debe == asiento_nc.total_haber


# ═══════════════════════════════════════════════════════════════════════════════
# 8. RUC Validation Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestRUCValidation:
    """RUC paraguayo format and check digit validation."""

    def test_ruc_valido(self):
        """80012345-0 should be valid (DV=0 by mod 11)."""
        # Should not raise
        validar_ruc_paraguayo('80012345-0')

    def test_ruc_vacio_permitido(self):
        """Empty RUC should be allowed."""
        validar_ruc_paraguayo('')

    def test_ruc_formato_invalido(self):
        with pytest.raises(ValidationError):
            validar_ruc_paraguayo('ABCDEF')

    def test_ruc_dv_invalido(self):
        with pytest.raises(ValidationError, match='dígito verificador|inv'):
            validar_ruc_paraguayo('80012345-9')  # DV should be 0, not 9


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Aging Report Tests
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestAgingReport:
    """Aging report endpoint for CxC."""

    def test_aging_endpoint(self, empresa_context, venta_borrador, stock_test):
        client, empresa = empresa_context
        VentaService.confirmar_venta(venta_borrador)

        url = reverse('cuentaporcobrar-aging')
        response = client.get(f"{url}?empresa={empresa.id}")
        assert response.status_code == status.HTTP_200_OK
        assert 'corriente' in response.data
        assert 'tramo_0_30' in response.data
        assert 'tramo_31_60' in response.data
        assert 'tramo_61_90' in response.data
        assert 'tramo_90_plus' in response.data


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Full Flow Integration Test
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestFullFlowWithAccounting:
    """Complete flow: sale → confirm (stock + asiento) → payment (asiento) → NC."""

    def test_flujo_completo(self, empresa_context, venta_borrador, stock_test, plan_cuentas, cliente_test, producto_test):
        client, empresa = empresa_context

        # 1. Confirm sale via API
        url_conf = reverse('venta-confirmar', kwargs={'pk': str(venta_borrador.id)})
        resp = client.post(f"{url_conf}?empresa={empresa.id}")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['estado'] == 'confirmada'

        # 2. Verify stock deducted
        stock_test.refresh_from_db()
        assert stock_test.cantidad == Decimal('98')

        # 3. Verify CxC created
        cxc = CuentaPorCobrar.objects.filter(venta=venta_borrador).first()
        assert cxc is not None

        # 4. Verify accounting entry
        asiento = Asiento.objects.filter(venta=venta_borrador).first()
        assert asiento is not None
        assert asiento.total_debe == asiento.total_haber

        # 5. Create and confirm payment
        pago = Pago.objects.create(
            empresa=empresa, venta=venta_borrador,
            cliente=cliente_test, fecha=date.today(),
            monto=venta_borrador.total, metodo='transferencia',
        )
        url_pago = reverse('pago-confirmar', kwargs={'pk': str(pago.id)})
        resp = client.post(f"{url_pago}?empresa={empresa.id}")
        assert resp.status_code == status.HTTP_200_OK

        # 6. Verify venta is paid
        venta_borrador.refresh_from_db()
        assert venta_borrador.estado == 'pagada'

        # 7. Verify 2 accounting entries total
        assert Asiento.objects.filter(empresa=empresa).count() == 2

    def test_nota_credito_api(self, empresa_context, venta_borrador, stock_test, plan_cuentas, cliente_test, producto_test):
        client, empresa = empresa_context

        # Confirm sale first
        VentaService.confirmar_venta(venta_borrador)

        # Create NC via API
        url_nc = reverse('nota-credito-list')
        nc_data = {
            'numero': 'NC-API-001',
            'venta_original': str(venta_borrador.id),
            'cliente': str(cliente_test.id),
            'fecha': str(date.today()),
            'motivo': 'devolucion',
            'descripcion': 'Test NC via API',
        }
        resp = client.post(f"{url_nc}?empresa={empresa.id}", nc_data)
        assert resp.status_code == status.HTTP_201_CREATED
        nc_id = resp.data['id']

        # Add line via API
        url_linea = reverse('nota-credito-agregar-linea', kwargs={'pk': nc_id})
        linea_data = {
            'producto': str(producto_test.id),
            'cantidad': '1',
            'precio_unitario': '50000',
            'condicion_iva': 'gravada_10',
        }
        resp = client.post(f"{url_linea}?empresa={empresa.id}", linea_data)
        assert resp.status_code == status.HTTP_201_CREATED

        # Confirm NC via API
        url_confirmar = reverse('nota-credito-confirmar', kwargs={'pk': nc_id})
        resp = client.post(f"{url_confirmar}?empresa={empresa.id}")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['estado'] == 'confirmada'
