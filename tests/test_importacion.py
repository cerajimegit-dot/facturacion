"""Tests for Excel import validators and import logic."""
import pytest
import os
import tempfile
from decimal import Decimal
from datetime import date

import pandas as pd
from django.test import override_settings

from apps.empresas.models import Empresa
from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.inventario.models import Almacen, Stock
from apps.ventas.models import Venta, LineaVenta
from apps.importacion.validators import (
    validate_clientes_row, validate_productos_row,
    validate_stock_row, validate_ventas_row,
    ValidationResult,
)
from apps.importacion.tasks import (
    _import_clientes, _import_productos, _import_stock, _import_ventas,
)


# ─── Validator unit tests ───────────────────────────────────────────

class TestValidateClientesRow:
    def test_fila_valida(self):
        row = {'nombre': 'Juan', 'ruc': '12345-6', 'email': 'j@test.com'}
        result = validate_clientes_row(row, 2)
        assert result.is_valid
        assert result.data['nombre'] == 'Juan'

    def test_nombre_vacio(self):
        row = {'nombre': '', 'ruc': '12345-6'}
        result = validate_clientes_row(row, 2)
        assert not result.is_valid
        assert any('nombre' in e for e in result.errors)

    def test_ruc_vacio(self):
        row = {'nombre': 'Juan', 'ruc': ''}
        result = validate_clientes_row(row, 2)
        assert not result.is_valid
        assert any('ruc' in e for e in result.errors)

    def test_email_invalido(self):
        row = {'nombre': 'Juan', 'ruc': '12345-6', 'email': 'not-an-email'}
        result = validate_clientes_row(row, 2)
        assert not result.is_valid
        assert any('email' in e for e in result.errors)

    def test_ruc_duplicado_warning(self):
        row = {'nombre': 'Juan', 'ruc': '12345-6'}
        result = validate_clientes_row(row, 2, existing_rucs={'12345-6'})
        assert result.is_valid  # Still valid but has warning
        assert result.has_warnings

    def test_tipo_cliente_invalido_warning(self):
        row = {'nombre': 'Juan', 'ruc': '12345-6', 'tipo_cliente': 'desconocido'}
        result = validate_clientes_row(row, 2)
        assert result.has_warnings
        assert result.data['tipo_cliente'] == 'persona'


class TestValidateProductosRow:
    def test_fila_valida(self):
        row = {'sku': 'P001', 'nombre': 'Producto', 'precio_unitario': '50000'}
        result = validate_productos_row(row, 2)
        assert result.is_valid
        assert result.data['precio_unitario'] == Decimal('50000')

    def test_sku_vacio(self):
        row = {'sku': '', 'nombre': 'Producto', 'precio_unitario': '50000'}
        result = validate_productos_row(row, 2)
        assert not result.is_valid

    def test_precio_negativo(self):
        row = {'sku': 'P001', 'nombre': 'Producto', 'precio_unitario': '-100'}
        result = validate_productos_row(row, 2)
        assert not result.is_valid
        assert any('negativo' in e for e in result.errors)

    def test_precio_invalido(self):
        row = {'sku': 'P001', 'nombre': 'Producto', 'precio_unitario': 'abc'}
        result = validate_productos_row(row, 2)
        assert not result.is_valid

    def test_sku_duplicado_warning(self):
        row = {'sku': 'P001', 'nombre': 'Producto', 'precio_unitario': '100'}
        result = validate_productos_row(row, 2, existing_skus={'P001'})
        assert result.has_warnings


class TestValidateStockRow:
    def test_fila_valida(self):
        row = {'sku': 'P001', 'almacen_codigo': 'ALM01', 'cantidad': '100'}
        result = validate_stock_row(row, 2, valid_skus={'P001'}, valid_almacenes={'ALM01'})
        assert result.is_valid

    def test_sku_no_existe(self):
        row = {'sku': 'NOEXIST', 'almacen_codigo': 'ALM01', 'cantidad': '100'}
        result = validate_stock_row(row, 2, valid_skus={'P001'}, valid_almacenes={'ALM01'})
        assert not result.is_valid

    def test_cantidad_negativa(self):
        row = {'sku': 'P001', 'almacen_codigo': 'ALM01', 'cantidad': '-5'}
        result = validate_stock_row(row, 2, valid_skus={'P001'}, valid_almacenes={'ALM01'})
        assert not result.is_valid


class TestValidateVentasRow:
    def test_fila_valida(self):
        row = {
            'numero': 'V001', 'fecha': '2025-01-15', 'cliente_ruc': '123-4',
            'sku': 'P001', 'cantidad': '5', 'precio_unitario': '10000',
        }
        result = validate_ventas_row(
            row, 2, valid_rucs={'123-4'}, valid_skus={'P001'}
        )
        assert result.is_valid

    def test_fecha_invalida(self):
        row = {
            'numero': 'V001', 'fecha': 'not-a-date', 'cliente_ruc': '123-4',
            'sku': 'P001', 'cantidad': '5', 'precio_unitario': '10000',
        }
        result = validate_ventas_row(row, 2)
        assert not result.is_valid

    def test_cantidad_cero(self):
        row = {
            'numero': 'V001', 'fecha': '2025-01-15', 'cliente_ruc': '123-4',
            'sku': 'P001', 'cantidad': '0', 'precio_unitario': '10000',
        }
        result = validate_ventas_row(row, 2)
        assert not result.is_valid
        assert any('mayor a 0' in e for e in result.errors)


# ─── Import function integration tests ──────────────────────────────

@pytest.mark.django_db
class TestImportClientes:
    def test_import_clientes_basico(self, empresa):
        df = pd.DataFrame([
            {'nombre': 'Cliente A', 'ruc': 'A-001', 'telefono': '0981111'},
            {'nombre': 'Cliente B', 'ruc': 'B-002', 'email': 'b@test.com'},
            {'nombre': 'Cliente C', 'ruc': 'C-003', 'tipo_cliente': 'empresa'},
        ])
        count, errors = _import_clientes(df, empresa)
        assert count == 3
        assert len(errors) == 0
        assert Cliente.objects.filter(empresa=empresa).count() == 3

    def test_import_clientes_duplicados(self, empresa):
        Cliente.objects.create(empresa=empresa, nombre='Existente', ruc='DUP-001')
        df = pd.DataFrame([
            {'nombre': 'Duplicado', 'ruc': 'DUP-001'},
            {'nombre': 'Nuevo', 'ruc': 'NEW-001'},
        ])
        count, errors = _import_clientes(df, empresa)
        assert count == 1
        assert len(errors) == 1

    def test_import_clientes_nombre_vacio(self, empresa):
        df = pd.DataFrame([
            {'nombre': '', 'ruc': 'EMPTY-001'},
        ])
        count, errors = _import_clientes(df, empresa)
        assert count == 0
        assert len(errors) == 1


@pytest.mark.django_db
class TestImportProductos:
    def test_import_productos_basico(self, empresa):
        df = pd.DataFrame([
            {'sku': 'SKU1', 'nombre': 'Producto 1', 'precio_unitario': 50000, 'costo': 30000},
            {'sku': 'SKU2', 'nombre': 'Producto 2', 'precio_unitario': 75000},
        ])
        count, errors = _import_productos(df, empresa)
        assert count == 2
        assert len(errors) == 0
        p = Producto.objects.get(empresa=empresa, sku='SKU1')
        assert p.precio_unitario == Decimal('50000')

    def test_import_productos_con_categoria(self, empresa):
        df = pd.DataFrame([
            {'sku': 'CAT1', 'nombre': 'Con Cat', 'precio_unitario': 100, 'categoria': 'Electrónica'},
        ])
        count, errors = _import_productos(df, empresa)
        assert count == 1
        from apps.productos.models import Categoria
        assert Categoria.objects.filter(empresa=empresa, nombre='Electrónica').exists()


@pytest.mark.django_db
class TestImportStock:
    def test_import_stock_basico(self, empresa):
        Producto.objects.create(empresa=empresa, sku='STK1', nombre='P Stock', precio_unitario=100)
        Almacen.objects.create(empresa=empresa, codigo='ALM1', nombre='Almacén 1')
        df = pd.DataFrame([
            {'sku': 'STK1', 'almacen_codigo': 'ALM1', 'cantidad': 50, 'ubicacion': 'A-1'},
        ])
        count, errors = _import_stock(df, empresa)
        assert count == 1
        assert len(errors) == 0
        stock = Stock.objects.get(empresa=empresa, producto__sku='STK1')
        assert stock.cantidad == Decimal('50')

    def test_import_stock_auto_crear_almacen(self, empresa):
        Producto.objects.create(empresa=empresa, sku='STK2', nombre='P2', precio_unitario=200)
        df = pd.DataFrame([
            {'sku': 'STK2', 'almacen_codigo': 'NUEVO', 'cantidad': 10},
        ])
        count, errors = _import_stock(df, empresa)
        assert count == 1
        assert Almacen.objects.filter(empresa=empresa, codigo='NUEVO').exists()


@pytest.mark.django_db
class TestImportVentas:
    def test_import_ventas_basico(self, empresa):
        Cliente.objects.create(empresa=empresa, nombre='CV', ruc='VRUC-1')
        Producto.objects.create(empresa=empresa, sku='VP1', nombre='PV', precio_unitario=1000)
        df = pd.DataFrame([
            {
                'numero': 'IMP-001', 'fecha': '2025-06-01',
                'cliente_ruc': 'VRUC-1', 'sku': 'VP1',
                'cantidad': 3, 'precio_unitario': 1000, 'impuestos': 10,
            },
        ])
        count, errors = _import_ventas(df, empresa)
        assert count == 1
        assert len(errors) == 0
        venta = Venta.objects.get(empresa=empresa, numero='IMP-001')
        assert venta.lineas.count() == 1
        assert venta.total > 0

    def test_import_ventas_multiples_lineas(self, empresa):
        Cliente.objects.create(empresa=empresa, nombre='CV2', ruc='VRUC-2')
        Producto.objects.create(empresa=empresa, sku='VP2', nombre='PV2', precio_unitario=500)
        Producto.objects.create(empresa=empresa, sku='VP3', nombre='PV3', precio_unitario=700)
        df = pd.DataFrame([
            {'numero': 'IMP-002', 'fecha': '2025-06-01', 'cliente_ruc': 'VRUC-2', 'sku': 'VP2', 'cantidad': 2, 'precio_unitario': 500, 'impuestos': 10},
            {'numero': 'IMP-002', 'fecha': '2025-06-01', 'cliente_ruc': 'VRUC-2', 'sku': 'VP3', 'cantidad': 1, 'precio_unitario': 700, 'impuestos': 10},
        ])
        count, errors = _import_ventas(df, empresa)
        assert count == 1  # 1 venta with 2 lines
        venta = Venta.objects.get(empresa=empresa, numero='IMP-002')
        assert venta.lineas.count() == 2


@pytest.mark.django_db
class TestImportExcelFile:
    """Integration test: create an actual Excel file and validate/import it."""

    def test_full_excel_import_workflow(self, empresa):
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            filepath = f.name

        try:
            # Create a multi-sheet workbook
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                pd.DataFrame([
                    {'nombre': 'Excel Client 1', 'ruc': 'XL-001', 'email': 'xl1@test.com'},
                    {'nombre': 'Excel Client 2', 'ruc': 'XL-002', 'telefono': '0981999'},
                ]).to_excel(writer, sheet_name='clientes', index=False)

                pd.DataFrame([
                    {'sku': 'XL-P1', 'nombre': 'Excel Prod 1', 'precio_unitario': 25000},
                    {'sku': 'XL-P2', 'nombre': 'Excel Prod 2', 'precio_unitario': 50000},
                ]).to_excel(writer, sheet_name='productos', index=False)

            # Import clientes
            df_cli = pd.read_excel(filepath, sheet_name='clientes')
            count_c, err_c = _import_clientes(df_cli, empresa)
            assert count_c == 2

            # Import productos
            df_prod = pd.read_excel(filepath, sheet_name='productos')
            count_p, err_p = _import_productos(df_prod, empresa)
            assert count_p == 2

            assert Cliente.objects.filter(empresa=empresa).count() == 2
            assert Producto.objects.filter(empresa=empresa).count() == 2

        finally:
            os.unlink(filepath)
