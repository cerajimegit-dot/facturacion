"""Test that all Streamlit pages import and their render functions exist."""
import sys
import os
sys.stdout.reconfigure(encoding='utf-8')

# Add frontend to path so imports work like Streamlit does
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'frontend'))

# Mock streamlit to avoid needing a running server
import unittest.mock as mock

# Create a comprehensive mock for streamlit
st_mock = mock.MagicMock()
st_mock.session_state = {
    "access_token": "fake_token",
    "refresh_token": "fake_refresh",
    "user": {"email": "test@test.com"},
    "empresa_activa": {"id": "fake-uuid", "codigo": "TEST", "nombre": "Test Corp"},
    "page": "dashboard",
}
sys.modules['streamlit'] = st_mock

# Mock plotly
px_mock = mock.MagicMock()
sys.modules['plotly'] = mock.MagicMock()
sys.modules['plotly.express'] = px_mock

# Mock extra deps
sys.modules['streamlit_option_menu'] = mock.MagicMock()
sys.modules['extra_streamlit_components'] = mock.MagicMock()

pages = [
    "pages.login",
    "pages.dashboard",
    "pages.empresas",
    "pages.clientes",
    "pages.productos",
    "pages.inventario",
    "pages.ventas",
    "pages.pagos",
    "pages.importacion",
    "pages.reportes",
    "pages.auditoria",
]

errors = []
for page_name in pages:
    try:
        mod = __import__(page_name, fromlist=['render'])
        assert hasattr(mod, 'render'), f"{page_name} missing render()"
        print(f"  [OK] {page_name}")
    except Exception as e:
        print(f"  [FAIL] {page_name}: {e}")
        errors.append(page_name)

# Also test helpers
try:
    import helpers
    assert hasattr(helpers, 'fmt')
    assert hasattr(helpers, 'results')
    assert helpers.fmt("50000.00", "$ ") == "$ 50,000"
    assert helpers.fmt(None) == "-"
    assert helpers.results({"count": 1, "results": [{"a": 1}]}) == [{"a": 1}]
    assert helpers.results([1, 2]) == [1, 2]
    assert helpers.results(None) == []
    print(f"  [OK] helpers")
except Exception as e:
    print(f"  [FAIL] helpers: {e}")
    errors.append("helpers")

# Also test api_client imports
try:
    import api_client as api
    funcs = [
        'login', 'register', 'get_perfil',
        'list_empresas', 'create_empresa', 'delete_empresa',
        'list_clientes', 'create_cliente', 'delete_cliente',
        'list_productos', 'create_producto', 'delete_producto',
        'list_categorias', 'create_categoria',
        'list_stock', 'list_almacenes', 'create_almacen', 'list_movimientos', 'create_movimiento',
        'list_ventas', 'get_venta', 'create_venta', 'confirmar_venta', 'anular_venta', 'agregar_linea_venta',
        'list_cotizaciones',
        'list_cuentas_por_cobrar', 'get_cxc_resumen', 'get_cxc_vencidas',
        'list_pagos', 'create_pago', 'confirmar_pago',
        'get_dashboard', 'get_reporte_ventas', 'get_reporte_cxc',
        'list_import_jobs', 'upload_import', 'validar_import', 'confirmar_import', 'cancelar_import',
        'list_auditoria',
    ]
    missing = [f for f in funcs if not hasattr(api, f)]
    if missing:
        print(f"  [FAIL] api_client: missing functions: {missing}")
        errors.append("api_client")
    else:
        print(f"  [OK] api_client ({len(funcs)} functions)")
except Exception as e:
    print(f"  [FAIL] api_client: {e}")
    errors.append("api_client")

print(f"\n{'='*50}")
if not errors:
    print("ALL IMPORTS OK!")
else:
    print(f"FAILED: {errors}")
sys.exit(len(errors))
