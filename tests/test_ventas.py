"""Tests for Ventas, CuentasPorCobrar, and payment flow."""
import pytest
from decimal import Decimal
from datetime import date
from django.urls import reverse
from rest_framework import status
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.ventas.models import Venta, LineaVenta, CuentaPorCobrar
from apps.pagos.models import Pago


@pytest.fixture
def cliente_test(empresa_context):
    _, empresa = empresa_context
    return Cliente.objects.create(
        empresa=empresa, nombre='Cliente Venta', ruc='99999-0'
    )


@pytest.fixture
def producto_test(empresa_context):
    _, empresa = empresa_context
    return Producto.objects.create(
        empresa=empresa, sku='PROD001', nombre='Producto Test',
        precio_unitario=Decimal('100000'), impuesto_porcentaje=Decimal('10'),
    )


@pytest.fixture
def venta_con_linea(empresa_context, cliente_test, producto_test):
    client, empresa = empresa_context
    venta = Venta.objects.create(
        empresa=empresa, numero='V-0001',
        cliente=cliente_test, fecha=date.today(),
        estado='borrador',
    )
    linea = LineaVenta(
        venta=venta, producto=producto_test,
        cantidad=Decimal('2'), precio_unitario=Decimal('100000'),
        impuesto_porcentaje=Decimal('10'),
    )
    linea.save()
    venta.recalcular_totales()
    return venta


@pytest.mark.django_db
class TestVentaCRUD:
    def test_crear_venta(self, empresa_context, cliente_test):
        client, empresa = empresa_context
        url = reverse('venta-list')
        data = {
            'numero': 'V-TEST01',
            'cliente': str(cliente_test.id),
            'fecha': '2025-01-15',
        }
        response = client.post(f"{url}?empresa={empresa.id}", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['numero'] == 'V-TEST01'

    def test_listar_ventas(self, empresa_context, venta_con_linea):
        client, empresa = empresa_context
        url = reverse('venta-list')
        response = client.get(f"{url}?empresa={empresa.id}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) >= 1

    def test_detalle_venta_con_lineas(self, empresa_context, venta_con_linea):
        client, empresa = empresa_context
        url = reverse('venta-detail', kwargs={'pk': str(venta_con_linea.id)})
        response = client.get(f"{url}?empresa={empresa.id}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['lineas']) == 1
        assert response.data['total'] == '220000.00'  # 200000 + 10% tax


@pytest.mark.django_db
class TestLineaVentaCalculo:
    def test_calculo_subtotal(self, empresa_context, producto_test):
        _, empresa = empresa_context
        venta = Venta.objects.create(
            empresa=empresa, numero='V-CALC',
            cliente=Cliente.objects.create(empresa=empresa, nombre='Calc', ruc='calc-1'),
            fecha=date.today(),
        )
        linea = LineaVenta(
            venta=venta, producto=producto_test,
            cantidad=Decimal('5'), precio_unitario=Decimal('50000'),
            impuesto_porcentaje=Decimal('10'),
        )
        linea.save()
        assert linea.subtotal == Decimal('250000')
        assert linea.impuesto_monto == Decimal('25000')
        assert linea.total == Decimal('275000')

    def test_calculo_con_descuento(self, empresa_context, producto_test):
        _, empresa = empresa_context
        venta = Venta.objects.create(
            empresa=empresa, numero='V-DESC',
            cliente=Cliente.objects.create(empresa=empresa, nombre='Desc', ruc='desc-1'),
            fecha=date.today(),
        )
        linea = LineaVenta(
            venta=venta, producto=producto_test,
            cantidad=Decimal('10'), precio_unitario=Decimal('10000'),
            descuento_porcentaje=Decimal('10'),
            impuesto_porcentaje=Decimal('10'),
        )
        linea.save()
        # subtotal = 10 * 10000 = 100000
        # descuento = 100000 * 10% = 10000
        # base = 90000
        # impuesto = 90000 * 10% = 9000
        # total = 90000 + 9000 = 99000
        assert linea.subtotal == Decimal('100000')
        assert linea.impuesto_monto == Decimal('9000')
        assert linea.total == Decimal('99000')


@pytest.mark.django_db
class TestConfirmarVenta:
    def test_confirmar_crea_cuenta_por_cobrar(self, empresa_context, venta_con_linea):
        client, empresa = empresa_context
        url = reverse('venta-confirmar', kwargs={'pk': str(venta_con_linea.id)})
        response = client.post(f"{url}?empresa={empresa.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data['estado'] == 'confirmada'
        # Verify CxC was created
        cxc = CuentaPorCobrar.objects.filter(venta=venta_con_linea).first()
        assert cxc is not None
        assert cxc.monto_original == venta_con_linea.total
        assert cxc.saldo == venta_con_linea.total

    def test_no_confirmar_venta_ya_confirmada(self, empresa_context, venta_con_linea):
        client, empresa = empresa_context
        venta_con_linea.estado = 'confirmada'
        venta_con_linea.save()
        url = reverse('venta-confirmar', kwargs={'pk': str(venta_con_linea.id)})
        response = client.post(f"{url}?empresa={empresa.id}")
        assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.django_db
class TestFlujoCompleto:
    def test_venta_pago_completo(self, empresa_context, venta_con_linea, cliente_test):
        """Test full flow: confirm sale -> register payment -> confirm payment."""
        client, empresa = empresa_context

        # 1. Confirm sale
        url = reverse('venta-confirmar', kwargs={'pk': str(venta_con_linea.id)})
        response = client.post(f"{url}?empresa={empresa.id}")
        assert response.data['estado'] == 'confirmada'
        total = Decimal(response.data['total'])

        # 2. Register payment
        pago_url = reverse('pago-list')
        pago_data = {
            'venta': str(venta_con_linea.id),
            'cliente': str(cliente_test.id),
            'fecha': '2025-01-15',
            'monto': str(total),
            'metodo': 'efectivo',
        }
        response = client.post(f"{pago_url}?empresa={empresa.id}", pago_data)
        assert response.status_code == status.HTTP_201_CREATED
        pago_id = response.data['id']

        # 3. Confirm payment
        confirmar_url = reverse('pago-confirmar', kwargs={'pk': pago_id})
        response = client.post(f"{confirmar_url}?empresa={empresa.id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.data['estado'] == 'confirmado'

        # 4. Verify sale is marked as paid
        venta_con_linea.refresh_from_db()
        assert venta_con_linea.estado == 'pagada'
        assert venta_con_linea.saldo_pendiente == 0

        # 5. Verify CxC is marked as paid
        cxc = CuentaPorCobrar.objects.filter(venta=venta_con_linea).first()
        assert cxc.estado == 'pagada'
        assert cxc.saldo == 0

    def test_pago_parcial(self, empresa_context, venta_con_linea, cliente_test):
        """Test partial payment flow."""
        client, empresa = empresa_context

        # Confirm sale
        url = reverse('venta-confirmar', kwargs={'pk': str(venta_con_linea.id)})
        client.post(f"{url}?empresa={empresa.id}")

        total = venta_con_linea.total
        pago_parcial = total / 2

        # Register partial payment
        pago_url = reverse('pago-list')
        pago_data = {
            'venta': str(venta_con_linea.id),
            'cliente': str(cliente_test.id),
            'fecha': '2025-01-15',
            'monto': str(pago_parcial),
            'metodo': 'transferencia',
        }
        response = client.post(f"{pago_url}?empresa={empresa.id}", pago_data)
        pago_id = response.data['id']

        # Confirm partial payment
        confirmar_url = reverse('pago-confirmar', kwargs={'pk': pago_id})
        client.post(f"{confirmar_url}?empresa={empresa.id}")

        venta_con_linea.refresh_from_db()
        assert venta_con_linea.estado == 'parcial'
        assert venta_con_linea.saldo_pendiente == total - pago_parcial
