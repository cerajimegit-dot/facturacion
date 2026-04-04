"""Tests for Compras (Purchases) module."""
import pytest
from decimal import Decimal
from datetime import date
from django.urls import reverse
from rest_framework import status
from apps.compras.models import Proveedor, CategoriaGasto, Compra, CompraDetalle, Gasto
from apps.inventario.models import Almacen
from apps.usuarios.models import Usuario


@pytest.fixture
def almacen_test(empresa_context):
    """Create a test warehouse."""
    _, empresa = empresa_context
    return Almacen.objects.create(
        empresa=empresa, codigo='ALM-001', nombre='Almacén Principal'
    )


@pytest.fixture
def proveedor_test(empresa_context):
    """Create a test supplier."""
    _, empresa = empresa_context
    return Proveedor.objects.create(
        empresa=empresa,
        nombre='Proveedor Test',
        ruc_numero='88888-0',
        pais='Paraguay'
    )


@pytest.fixture
def categoria_gasto_test():
    """Create a test expense category."""
    return CategoriaGasto.objects.create(
        nombre='Servicios Generales',
        descripcion='Gastos en servicios diversos'
    )


@pytest.fixture
def compra_test(empresa_context, proveedor_test, almacen_test):
    """Create a test purchase."""
    _, empresa = empresa_context
    return Compra.objects.create(
        empresa=empresa,
        numero='COM-001',
        fecha=date.today(),
        proveedor=proveedor_test,
        almacen=almacen_test,
        moneda='PYG',
        subtotal=Decimal('100000'),
        impuestos_total=Decimal('10000'),
        total=Decimal('110000'),
        estado='pendiente'
    )


@pytest.mark.django_db
class TestProveedorCRUD:
    """Tests for Supplier CRUD operations."""
    
    def test_crear_proveedor(self, empresa_context):
        """Test creating a supplier."""
        _, empresa = empresa_context
        proveedor = Proveedor.objects.create(
            empresa=empresa,
            nombre='Nuevo Proveedor',
            ruc_numero='12345-0',
            pais='Argentina'
        )
        assert proveedor.nombre == 'Nuevo Proveedor'
        assert proveedor.empresa == empresa
        assert proveedor.activo is True

    def test_proveedor_unico_por_empresa(self, empresa_context):
        """Test that RUC must be unique per empresa."""
        _, empresa = empresa_context
        Proveedor.objects.create(
            empresa=empresa,
            nombre='Proveedor 1',
            ruc_numero='12345-0',
            pais='Paraguay'
        )
        # Intenta crear otro con el mismo RUC en la misma empresa
        with pytest.raises(Exception):  # IntegrityError
            Proveedor.objects.create(
                empresa=empresa,
                nombre='Proveedor 2',
                ruc_numero='12345-0',
                pais='Paraguay'
            )

    def test_proveedor_total_compras(self, empresa_context, proveedor_test, almacen_test):
        """Test total_compras property."""
        _, empresa = empresa_context
        Compra.objects.create(
            empresa=empresa,
            numero='COM-001',
            fecha=date.today(),
            proveedor=proveedor_test,
            almacen=almacen_test,
            estado='recepcionada'
        )
        assert proveedor_test.total_compras == 1


@pytest.mark.django_db
class TestCompraCRUD:
    """Tests for Purchase CRUD operations."""
    
    def test_crear_compra(self, empresa_context, proveedor_test, almacen_test):
        """Test creating a purchase."""
        _, empresa = empresa_context
        compra = Compra.objects.create(
            empresa=empresa,
            numero='COM-001',
            fecha=date.today(),
            proveedor=proveedor_test,
            almacen=almacen_test,
            moneda='PYG',
            total=Decimal('110000')
        )
        assert compra.numero == 'COM-001'
        assert compra.estado == 'pendiente'

    def test_compra_cotizacion_usd_requerida(self, empresa_context, proveedor_test, almacen_test):
        """Test that USD exchange rate is required when currency is USD."""
        _, empresa = empresa_context
        compra = Compra(
            empresa=empresa,
            numero='COM-001',
            fecha=date.today(),
            proveedor=proveedor_test,
            almacen=almacen_test,
            moneda='USD',
            cotizacion_usd=None  # Sin cotización
        )
        with pytest.raises(ValueError, match="cotización USD"):
            compra.save()

    def test_compra_unica_numero_por_empresa(self, empresa_context, proveedor_test, almacen_test):
        """Test unique constraint on (empresa, numero, proveedor)."""
        _, empresa = empresa_context
        Compra.objects.create(
            empresa=empresa,
            numero='COM-001',
            fecha=date.today(),
            proveedor=proveedor_test,
            almacen=almacen_test
        )
        with pytest.raises(Exception):  # IntegrityError
            Compra.objects.create(
                empresa=empresa,
                numero='COM-001',
                fecha=date.today(),
                proveedor=proveedor_test,
                almacen=almacen_test
            )


@pytest.mark.django_db
class TestGastoCRUD:
    """Tests for Expense CRUD operations."""
    
    def test_crear_gasto(self, empresa_context, categoria_gasto_test):
        """Test creating an expense."""
        _, empresa = empresa_context
        gasto = Gasto.objects.create(
            empresa=empresa,
            fecha=date.today(),
            categoria=categoria_gasto_test,
            descripcion='Gasto test',
            monto=Decimal('50000'),
            moneda='PYG'
        )
        assert gasto.monto == Decimal('50000')
        assert gasto.aprobado is False

    def test_gasto_aprobado_flag(self, empresa_context, categoria_gasto_test):
        """Test expense approval flag."""
        _, empresa = empresa_context
        gasto = Gasto.objects.create(
            empresa=empresa,
            fecha=date.today(),
            categoria=categoria_gasto_test,
            monto=Decimal('50000'),
            aprobado=True
        )
        assert gasto.aprobado is True


@pytest.mark.django_db
class TestCategoriaGastoCRUD:
    """Tests for Expense Category CRUD operations."""
    
    def test_crear_categoria(self):
        """Test creating an expense category."""
        cat = CategoriaGasto.objects.create(
            nombre='Servicios',
            descripcion='Gastos de servicios'
        )
        assert cat.nombre == 'Servicios'
        assert cat.activo is True

    def test_categoria_nombre_unico(self):
        """Test that category name must be unique."""
        CategoriaGasto.objects.create(nombre='Servicios')
        with pytest.raises(Exception):  # IntegrityError
            CategoriaGasto.objects.create(nombre='Servicios')

