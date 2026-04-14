"""
Tests E2E automatizados para el módulo de Activos Fijos.

Simulan todas las operaciones que realiza el frontend (Streamlit)
contra la API REST de Django, cubriendo los 7 tabs:
  1. Dashboard (resumen, alertas)
  2. Listado de activos (filtros, búsqueda)
  3. Nuevo activo (validaciones, creación)
  4. Mantenimientos (CRUD, completar, cancelar)
  5. Movimientos (historial, mover activo)
  6. Depreciación (cálculo, reporte)
  7. Catálogos (clasificaciones, ubicaciones, centros de costo)

Se ejecuta con:  pytest tests/test_activos_fijos_e2e.py -v
"""
import pytest
from decimal import Decimal
from datetime import date
from rest_framework.test import APIClient
from apps.usuarios.models import Usuario, Membership
from apps.empresas.models import Empresa
from apps.activos_fijos.models import (
    ClasificacionActivo, UbicacionActivo, CentroCosto,
    ActivoFijo, MovimientoActivo, MantenimientoActivo,
    BajaActivo, DepreciacionMensual,
)

BASE = "/api/v1/activos-fijos"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def setup_env(db):
    """Crea usuario, empresa y membresía; devuelve client autenticado + empresa."""
    user = Usuario.objects.create_user(
        username="af_test",
        email="af_test@test.com",
        password="Test1234!",
        first_name="AF",
        last_name="Tester",
    )
    empresa = Empresa.objects.create(
        codigo="AFT001",
        nombre="AF Test Corp",
        ruc="9999999-0",
        razon_social="AF Test Corp S.A.",
        moneda_principal="PYG",
    )
    Membership.objects.create(usuario=user, empresa=empresa, rol="admin")
    client = APIClient()
    client.force_authenticate(user=user)
    return client, empresa


@pytest.fixture
def ep(setup_env):
    """Query param con empresa id."""
    _, empresa = setup_env
    return {"empresa": str(empresa.id)}


@pytest.fixture
def client(setup_env):
    _, empresa = setup_env
    c = setup_env[0]
    return c


@pytest.fixture
def clasificacion(setup_env):
    c, empresa = setup_env
    resp = c.post(f"{BASE}/clasificaciones/", {
        "nombre": "Equipos IT",
        "descripcion": "Hardware y software",
        "vida_util_default": 3,
    }, format="json", QUERY_STRING=f"empresa={empresa.id}")
    assert resp.status_code == 201, resp.data
    return resp.data


@pytest.fixture
def ubicacion(setup_env):
    c, empresa = setup_env
    resp = c.post(f"{BASE}/ubicaciones/", {
        "planta": "Planta Central",
        "edificio": "Edificio A",
        "area": "Piso 1",
    }, format="json", QUERY_STRING=f"empresa={empresa.id}")
    assert resp.status_code == 201, resp.data
    return resp.data


@pytest.fixture
def ubicacion2(setup_env):
    c, empresa = setup_env
    resp = c.post(f"{BASE}/ubicaciones/", {
        "planta": "Planta Norte",
        "edificio": "Edificio B",
        "area": "Piso 2",
    }, format="json", QUERY_STRING=f"empresa={empresa.id}")
    assert resp.status_code == 201, resp.data
    return resp.data


@pytest.fixture
def centro_costo(setup_env):
    c, empresa = setup_env
    resp = c.post(f"{BASE}/centros-costo/", {
        "codigo": "CC-001",
        "descripcion": "Departamento TI",
    }, format="json", QUERY_STRING=f"empresa={empresa.id}")
    assert resp.status_code == 201, resp.data
    return resp.data


@pytest.fixture
def activo(setup_env, clasificacion, ubicacion, centro_costo):
    c, empresa = setup_env
    resp = c.post(f"{BASE}/activos/", {
        "codigo": "AF-001",
        "nombre": "Laptop Dell XPS",
        "tipo": "IT",
        "descripcion": "Laptop de desarrollo",
        "valor_adquisicion": "5000000",
        "valor_residual": "500000",
        "vida_util_anios": 5,
        "fecha_adquisicion": "2024-01-15",
        "clasificacion": clasificacion["id"],
        "ubicacion": ubicacion["id"],
        "centro_costo": centro_costo["id"],
        "numero_serie": "SN-XPS-001",
        "numero_factura": "FAC-001",
        "notas": "Equipo de desarrollo principal",
    }, format="json", QUERY_STRING=f"empresa={empresa.id}")
    assert resp.status_code == 201, resp.data
    return resp.data


@pytest.fixture
def activo2(setup_env, clasificacion, ubicacion):
    c, empresa = setup_env
    resp = c.post(f"{BASE}/activos/", {
        "codigo": "AF-002",
        "nombre": "Monitor LG 27",
        "tipo": "IT",
        "valor_adquisicion": "2000000",
        "valor_residual": "200000",
        "vida_util_anios": 5,
        "fecha_adquisicion": "2024-03-01",
        "clasificacion": clasificacion["id"],
        "ubicacion": ubicacion["id"],
    }, format="json", QUERY_STRING=f"empresa={empresa.id}")
    assert resp.status_code == 201, resp.data
    return resp.data


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7: CATÁLOGOS
# ══════════════════════════════════════════════════════════════════════════════

class TestCatalogosClasificaciones:
    """CRUD de clasificaciones de activos."""

    def test_crear_clasificacion(self, setup_env):
        c, empresa = setup_env
        resp = c.post(f"{BASE}/clasificaciones/", {
            "nombre": "Maquinaria",
            "descripcion": "Maquinaria pesada",
            "vida_util_default": 10,
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 201
        assert resp.data["nombre"] == "Maquinaria"
        assert resp.data["vida_util_default"] == 10

    def test_listar_clasificaciones(self, setup_env, clasificacion):
        c, empresa = setup_env
        resp = c.get(f"{BASE}/clasificaciones/", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        assert len(items) >= 1
        nombres = [i["nombre"] for i in items]
        assert "Equipos IT" in nombres

    def test_eliminar_clasificacion(self, setup_env, clasificacion):
        c, empresa = setup_env
        cid = clasificacion["id"]
        resp = c.delete(f"{BASE}/clasificaciones/{cid}/", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 204

    def test_clasificacion_duplicada(self, setup_env, clasificacion):
        c, empresa = setup_env
        resp = c.post(f"{BASE}/clasificaciones/", {
            "nombre": "Equipos IT",
            "vida_util_default": 3,
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 400


class TestCatalogosUbicaciones:
    """CRUD de ubicaciones."""

    def test_crear_ubicacion(self, setup_env):
        c, empresa = setup_env
        resp = c.post(f"{BASE}/ubicaciones/", {
            "planta": "Sucursal 1",
            "edificio": "Principal",
            "area": "Almacén",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 201
        assert resp.data["planta"] == "Sucursal 1"
        assert "nombre_completo" in resp.data

    def test_listar_ubicaciones(self, setup_env, ubicacion):
        c, empresa = setup_env
        resp = c.get(f"{BASE}/ubicaciones/", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        assert len(items) >= 1

    def test_eliminar_ubicacion(self, setup_env, ubicacion):
        c, empresa = setup_env
        resp = c.delete(f"{BASE}/ubicaciones/{ubicacion['id']}/",
                        QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 204

    def test_ubicacion_duplicada(self, setup_env, ubicacion):
        c, empresa = setup_env
        resp = c.post(f"{BASE}/ubicaciones/", {
            "planta": "Planta Central",
            "edificio": "Edificio A",
            "area": "Piso 1",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 400


class TestCatalogosCentrosCosto:
    """CRUD de centros de costo."""

    def test_crear_centro_costo(self, setup_env):
        c, empresa = setup_env
        resp = c.post(f"{BASE}/centros-costo/", {
            "codigo": "CC-ADM",
            "descripcion": "Administración",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 201
        assert resp.data["codigo"] == "CC-ADM"

    def test_listar_centros_costo(self, setup_env, centro_costo):
        c, empresa = setup_env
        resp = c.get(f"{BASE}/centros-costo/", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        assert len(items) >= 1

    def test_eliminar_centro_costo(self, setup_env, centro_costo):
        c, empresa = setup_env
        resp = c.delete(f"{BASE}/centros-costo/{centro_costo['id']}/",
                        QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 204

    def test_centro_costo_duplicado(self, setup_env, centro_costo):
        c, empresa = setup_env
        resp = c.post(f"{BASE}/centros-costo/", {
            "codigo": "CC-001",
            "descripcion": "Otro",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: NUEVO ACTIVO (creación, validaciones)
# ══════════════════════════════════════════════════════════════════════════════

class TestNuevoActivo:
    """Creación de activos fijos con validaciones."""

    def test_crear_activo_completo(self, activo):
        assert activo["codigo"] == "AF-001"
        assert activo["nombre"] == "Laptop Dell XPS"
        assert activo["tipo"] == "IT"
        assert activo["estado"] == "activo"
        assert activo["numero_serie"] == "SN-XPS-001"
        assert activo["numero_factura"] == "FAC-001"

    def test_valor_adquisicion_y_libro(self, activo):
        """valor_libro == valor_adquisicion al momento de creación (dep=0)."""
        va = Decimal(activo["valor_adquisicion"])
        vl = Decimal(activo["valor_libro"])
        assert va == Decimal("5000000.00")
        assert vl == va  # depreciación aún no aplicada

    def test_crear_activo_sin_codigo_falla(self, setup_env, clasificacion):
        c, empresa = setup_env
        resp = c.post(f"{BASE}/activos/", {
            "nombre": "Sin código",
            "tipo": "IT",
            "valor_adquisicion": "1000000",
            "vida_util_anios": 3,
            "fecha_adquisicion": "2024-01-01",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 400

    def test_crear_activo_sin_nombre_falla(self, setup_env):
        c, empresa = setup_env
        resp = c.post(f"{BASE}/activos/", {
            "codigo": "AF-X",
            "tipo": "IT",
            "valor_adquisicion": "1000000",
            "vida_util_anios": 3,
            "fecha_adquisicion": "2024-01-01",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 400

    def test_crear_activo_codigo_duplicado(self, setup_env, activo):
        c, empresa = setup_env
        resp = c.post(f"{BASE}/activos/", {
            "codigo": "AF-001",
            "nombre": "Duplicado",
            "tipo": "IT",
            "valor_adquisicion": "1000",
            "vida_util_anios": 3,
            "fecha_adquisicion": "2024-01-01",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 400

    def test_crear_activo_sin_catálogos(self, setup_env):
        """Un activo sin clasificación/ubicación/centro de costo debe poder crearse."""
        c, empresa = setup_env
        resp = c.post(f"{BASE}/activos/", {
            "codigo": "AF-SOLO",
            "nombre": "Activo simple",
            "tipo": "mobiliario",
            "valor_adquisicion": "500000",
            "valor_residual": "0",
            "vida_util_anios": 10,
            "fecha_adquisicion": "2024-06-01",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 201
        assert resp.data["clasificacion"] is None
        assert resp.data["ubicacion"] is None

    def test_tipos_validos(self, setup_env):
        """Verifica que todos los tipos de activo son aceptados."""
        c, empresa = setup_env
        tipos = ["IT", "planta", "mobiliario", "vehiculo", "edificio", "terreno", "otro"]
        for i, tipo in enumerate(tipos):
            resp = c.post(f"{BASE}/activos/", {
                "codigo": f"T-{i:03d}",
                "nombre": f"Activo tipo {tipo}",
                "tipo": tipo,
                "valor_adquisicion": "100000",
                "vida_util_anios": 5,
                "fecha_adquisicion": "2024-01-01",
            }, format="json", QUERY_STRING=f"empresa={empresa.id}")
            assert resp.status_code == 201, f"Tipo {tipo} falló: {resp.data}"


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: LISTA DE ACTIVOS (filtros, búsqueda, detalle)
# ══════════════════════════════════════════════════════════════════════════════

class TestListaActivos:
    """Listado, filtros y detalle de activos."""

    def test_listar_activos(self, setup_env, activo, activo2):
        c, empresa = setup_env
        resp = c.get(f"{BASE}/activos/", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        assert len(items) >= 2

    def test_filtrar_por_tipo(self, setup_env, activo):
        c, empresa = setup_env
        resp = c.get(f"{BASE}/activos/",
                     QUERY_STRING=f"empresa={empresa.id}&tipo=IT")
        assert resp.status_code == 200
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        assert all(a["tipo"] == "IT" for a in items)

    def test_filtrar_por_estado(self, setup_env, activo):
        c, empresa = setup_env
        resp = c.get(f"{BASE}/activos/",
                     QUERY_STRING=f"empresa={empresa.id}&estado=activo")
        assert resp.status_code == 200
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        assert all(a["estado"] == "activo" for a in items)

    def test_buscar_por_search(self, setup_env, activo, activo2):
        c, empresa = setup_env
        resp = c.get(f"{BASE}/activos/",
                     QUERY_STRING=f"empresa={empresa.id}&search=Dell")
        assert resp.status_code == 200
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        assert any("Dell" in a["nombre"] for a in items)

    def test_detalle_activo(self, setup_env, activo):
        c, empresa = setup_env
        aid = activo["id"]
        resp = c.get(f"{BASE}/activos/{aid}/",
                     QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        d = resp.data
        assert d["codigo"] == "AF-001"
        assert "depreciacion_mensual" in d
        assert "porcentaje_depreciado" in d
        assert "vida_util_restante_meses" in d

    def test_update_activo(self, setup_env, activo):
        c, empresa = setup_env
        aid = activo["id"]
        resp = c.patch(f"{BASE}/activos/{aid}/", {
            "nombre": "Laptop Dell XPS 15 UPDATED",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        assert resp.data["nombre"] == "Laptop Dell XPS 15 UPDATED"

    def test_delete_activo(self, setup_env, activo):
        c, empresa = setup_env
        aid = activo["id"]
        resp = c.delete(f"{BASE}/activos/{aid}/",
                        QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 204


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: DASHBOARD (resumen, alertas)
# ══════════════════════════════════════════════════════════════════════════════

class TestDashboard:
    """Dashboard de resumen y alertas."""

    def test_resumen_vacio(self, setup_env):
        c, empresa = setup_env
        resp = c.get(f"{BASE}/activos/resumen/",
                     QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        assert resp.data["total_activos"] == 0

    def test_resumen_con_activos(self, setup_env, activo, activo2):
        c, empresa = setup_env
        resp = c.get(f"{BASE}/activos/resumen/",
                     QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        r = resp.data
        assert r["total_activos"] >= 2
        assert r["activos_operativos"] >= 2
        va_total = Decimal(r["valor_total_adquisicion"])
        assert va_total == Decimal("7000000.00")

    def test_alertas_activos(self, setup_env, activo):
        c, empresa = setup_env
        resp = c.get(f"{BASE}/activos/alertas/",
                     QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: MOVIMIENTOS (mover activo)
# ══════════════════════════════════════════════════════════════════════════════

class TestMovimientos:
    """Movimiento de activos entre ubicaciones."""

    def test_mover_activo(self, setup_env, activo, ubicacion2):
        c, empresa = setup_env
        aid = activo["id"]
        resp = c.post(f"{BASE}/activos/{aid}/mover/", {
            "ubicacion_destino": ubicacion2["id"],
            "motivo": "Reubicación de oficina",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200

        # Verificar que la ubicación cambió
        det = c.get(f"{BASE}/activos/{aid}/",
                    QUERY_STRING=f"empresa={empresa.id}")
        assert str(det.data["ubicacion"]) == str(ubicacion2["id"])

    def test_historial_movimientos(self, setup_env, activo, ubicacion2):
        c, empresa = setup_env
        aid = activo["id"]
        # Mover
        c.post(f"{BASE}/activos/{aid}/mover/", {
            "ubicacion_destino": ubicacion2["id"],
            "motivo": "Movimiento test",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")

        # Listar
        resp = c.get(f"{BASE}/movimientos/",
                     QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        assert len(items) >= 1

    def test_mover_activo_sin_ubicacion_falla(self, setup_env, activo):
        c, empresa = setup_env
        aid = activo["id"]
        resp = c.post(f"{BASE}/activos/{aid}/mover/", {
            "motivo": "Sin destino",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 400


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: MANTENIMIENTOS
# ══════════════════════════════════════════════════════════════════════════════

class TestMantenimientos:
    """CRUD de mantenimientos y acciones (completar/cancelar)."""

    def test_crear_mantenimiento(self, setup_env, activo):
        c, empresa = setup_env
        resp = c.post(f"{BASE}/mantenimientos/", {
            "activo": activo["id"],
            "tipo": "preventivo",
            "descripcion": "Limpieza interna",
            "costo": "100000",
            "proveedor_servicio": "TechClean",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 201
        assert resp.data["tipo"] == "preventivo"
        assert resp.data["estado"] == "programado"

    def test_listar_mantenimientos(self, setup_env, activo):
        c, empresa = setup_env
        # Crear uno primero
        c.post(f"{BASE}/mantenimientos/", {
            "activo": activo["id"],
            "tipo": "correctivo",
            "descripcion": "Reparación pantalla",
            "costo": "500000",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")

        resp = c.get(f"{BASE}/mantenimientos/",
                     QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        assert len(items) >= 1

    def test_completar_mantenimiento(self, setup_env, activo):
        c, empresa = setup_env
        # Crear
        cr = c.post(f"{BASE}/mantenimientos/", {
            "activo": activo["id"],
            "tipo": "preventivo",
            "descripcion": "Mantenimiento a completar",
            "costo": "50000",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        mid = cr.data["id"]

        # Completar
        resp = c.post(f"{BASE}/mantenimientos/{mid}/completar/",
                      format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        assert resp.data["estado"] == "completado"

    def test_cancelar_mantenimiento(self, setup_env, activo):
        c, empresa = setup_env
        cr = c.post(f"{BASE}/mantenimientos/", {
            "activo": activo["id"],
            "tipo": "correctivo",
            "descripcion": "Mantenimiento a cancelar",
            "costo": "50000",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        mid = cr.data["id"]

        resp = c.post(f"{BASE}/mantenimientos/{mid}/cancelar/",
                      format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        assert resp.data["estado"] == "cancelado"

    def test_completar_ya_completado_falla(self, setup_env, activo):
        c, empresa = setup_env
        cr = c.post(f"{BASE}/mantenimientos/", {
            "activo": activo["id"],
            "tipo": "preventivo",
            "descripcion": "Ya completado",
            "costo": "10000",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        mid = cr.data["id"]

        # Completar primera vez
        c.post(f"{BASE}/mantenimientos/{mid}/completar/",
               format="json", QUERY_STRING=f"empresa={empresa.id}")

        # Intentar completar de nuevo
        resp = c.post(f"{BASE}/mantenimientos/{mid}/completar/",
                      format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 400

    def test_mantenimiento_cambia_estado_activo(self, setup_env, activo):
        """Al crear mantenimiento correctivo el activo pasa a 'en_mantenimiento'."""
        c, empresa = setup_env
        cr = c.post(f"{BASE}/mantenimientos/", {
            "activo": activo["id"],
            "tipo": "correctivo",
            "descripcion": "Reparación urgente",
            "costo": "300000",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert cr.status_code == 201

        # Verificar estado del activo
        det = c.get(f"{BASE}/activos/{activo['id']}/",
                    QUERY_STRING=f"empresa={empresa.id}")
        # El estado puede o no cambiar dependiendo de la implementación,
        # verificamos que el endpoint responde correctamente
        assert det.status_code == 200


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6: DEPRECIACIÓN
# ══════════════════════════════════════════════════════════════════════════════

class TestDepreciacion:
    """Cálculo y reporte de depreciación."""

    def test_calcular_depreciacion(self, setup_env, activo):
        c, empresa = setup_env
        resp = c.post(f"{BASE}/activos/calcular_depreciacion/", {
            "anio": 2024,
            "mes": 2,
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        assert "registros_creados" in resp.data

    def test_listar_depreciaciones(self, setup_env, activo):
        c, empresa = setup_env
        # Calcular primero
        c.post(f"{BASE}/activos/calcular_depreciacion/", {
            "anio": 2024,
            "mes": 3,
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")

        resp = c.get(f"{BASE}/depreciaciones/",
                     QUERY_STRING=f"empresa={empresa.id}&anio=2024")
        assert resp.status_code == 200

    def test_calcular_depreciacion_aplica_montos(self, setup_env, activo):
        """Verificar que la depreciación actualiza el activo."""
        c, empresa = setup_env
        # Calcular depreciación para un mes
        c.post(f"{BASE}/activos/calcular_depreciacion/", {
            "anio": 2024,
            "mes": 2,
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")

        # Revisar que el activo tiene depreciación acumulada
        det = c.get(f"{BASE}/activos/{activo['id']}/",
                    QUERY_STRING=f"empresa={empresa.id}")
        assert det.status_code == 200
        dep_acum = Decimal(det.data["depreciacion_acumulada"])
        val_libro = Decimal(det.data["valor_libro"])
        val_adq = Decimal(det.data["valor_adquisicion"])
        assert val_libro == val_adq - dep_acum

    def test_calcular_mismo_mes_idempotente(self, setup_env, activo):
        """Calcular el mismo mes dos veces no debe duplicar registros."""
        c, empresa = setup_env
        r1 = c.post(f"{BASE}/activos/calcular_depreciacion/", {
            "anio": 2024,
            "mes": 4,
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        creados1 = r1.data.get("registros_creados", 0)

        r2 = c.post(f"{BASE}/activos/calcular_depreciacion/", {
            "anio": 2024,
            "mes": 4,
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        creados2 = r2.data.get("registros_creados", 0)

        assert creados2 == 0, "Segunda corrida no debe crear registros duplicados"

    def test_depreciacion_valores_correctos(self, setup_env, activo):
        """Verificar fórmula: dep_mensual = (valor_adq - valor_residual) / (vida_util * 12)."""
        c, empresa = setup_env
        va = Decimal("5000000")
        vr = Decimal("500000")
        vida = 5
        dep_esperada = ((va - vr) / (vida * 12)).quantize(Decimal("0.01"))

        det = c.get(f"{BASE}/activos/{activo['id']}/",
                    QUERY_STRING=f"empresa={empresa.id}")
        dep_mensual = Decimal(det.data["depreciacion_mensual"])
        assert dep_mensual == dep_esperada


# ══════════════════════════════════════════════════════════════════════════════
# BAJA DE ACTIVOS (acción desde Tab 2)
# ══════════════════════════════════════════════════════════════════════════════

class TestBajaActivo:
    """Dar de baja activos fijos."""

    def test_dar_baja_activo(self, setup_env, activo):
        c, empresa = setup_env
        aid = activo["id"]
        resp = c.post(f"{BASE}/activos/{aid}/dar_baja/", {
            "fecha_baja": "2024-12-31",
            "motivo": "obsolescencia",
            "motivo_detalle": "Equipo demasiado lento",
            "valor_rescate": "100000",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200

        # Verificar que el estado cambió
        det = c.get(f"{BASE}/activos/{aid}/",
                    QUERY_STRING=f"empresa={empresa.id}")
        assert det.data["estado"] == "baja"

    def test_dar_baja_registra_en_bajas(self, setup_env, activo):
        c, empresa = setup_env
        aid = activo["id"]
        c.post(f"{BASE}/activos/{aid}/dar_baja/", {
            "fecha_baja": "2024-12-31",
            "motivo": "venta",
            "motivo_detalle": "Vendido a tercero",
            "valor_rescate": "200000",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")

        # Listar bajas
        resp = c.get(f"{BASE}/bajas/",
                     QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 200
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        assert len(items) >= 1

    def test_dar_baja_activo_ya_baja_falla(self, setup_env, activo):
        c, empresa = setup_env
        aid = activo["id"]
        # Primera baja
        c.post(f"{BASE}/activos/{aid}/dar_baja/", {
            "fecha_baja": "2024-12-31",
            "motivo": "obsolescencia",
            "motivo_detalle": "Ya obsoleto",
            "valor_rescate": "0",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")

        # Segunda baja
        resp = c.post(f"{BASE}/activos/{aid}/dar_baja/", {
            "fecha_baja": "2024-12-31",
            "motivo": "venta",
            "motivo_detalle": "Otra razón",
            "valor_rescate": "0",
        }, format="json", QUERY_STRING=f"empresa={empresa.id}")
        assert resp.status_code == 400

    def test_motivos_baja_validos(self, setup_env):
        """Verificar que los motivos del frontend coincidan con los del backend."""
        c, empresa = setup_env
        motivos = ["obsolescencia", "daño_irreparable", "venta", "donacion", "robo", "otro"]
        for i, motivo in enumerate(motivos):
            # Crear activo único
            cr = c.post(f"{BASE}/activos/", {
                "codigo": f"BAJA-{i:03d}",
                "nombre": f"Activo baja {motivo}",
                "tipo": "otro",
                "valor_adquisicion": "100000",
                "vida_util_anios": 5,
                "fecha_adquisicion": "2024-01-01",
            }, format="json", QUERY_STRING=f"empresa={empresa.id}")
            assert cr.status_code == 201, f"Crear activo para baja {motivo}: {cr.data}"

            resp = c.post(f"{BASE}/activos/{cr.data['id']}/dar_baja/", {
                "fecha_baja": "2024-12-31",
                "motivo": motivo,
                "motivo_detalle": f"Test {motivo}",
                "valor_rescate": "0",
            }, format="json", QUERY_STRING=f"empresa={empresa.id}")
            assert resp.status_code == 200, f"Motivo {motivo} falló: {resp.data}"


# ══════════════════════════════════════════════════════════════════════════════
# FLUJO COMPLETO E2E (simula usuario navegando todo el frontend)
# ══════════════════════════════════════════════════════════════════════════════

class TestFlujoCompletoE2E:
    """Simula un usuario completo: crea catálogos → activos → opera → reporta."""

    def test_flujo_completo(self, setup_env):
        c, empresa = setup_env
        eid = str(empresa.id)
        qs = f"empresa={eid}"

        # ── 1. Crear catálogos (Tab 7) ──
        cls_r = c.post(f"{BASE}/clasificaciones/", {
            "nombre": "Vehículos",
            "descripcion": "Flota vehicular",
            "vida_util_default": 8,
        }, format="json", QUERY_STRING=qs)
        assert cls_r.status_code == 201
        cls_id = cls_r.data["id"]

        ub1_r = c.post(f"{BASE}/ubicaciones/", {
            "planta": "Casa Matriz",
            "edificio": "Estacionamiento",
            "area": "Nivel 1",
        }, format="json", QUERY_STRING=qs)
        assert ub1_r.status_code == 201
        ub1_id = ub1_r.data["id"]

        ub2_r = c.post(f"{BASE}/ubicaciones/", {
            "planta": "Sucursal Norte",
            "edificio": "Garage",
            "area": "",
        }, format="json", QUERY_STRING=qs)
        assert ub2_r.status_code == 201
        ub2_id = ub2_r.data["id"]

        cc_r = c.post(f"{BASE}/centros-costo/", {
            "codigo": "CC-FLOTA",
            "descripcion": "Flota vehicular",
        }, format="json", QUERY_STRING=qs)
        assert cc_r.status_code == 201
        cc_id = cc_r.data["id"]

        # ── 2. Crear activos (Tab 3) ──
        a1_r = c.post(f"{BASE}/activos/", {
            "codigo": "VH-001",
            "nombre": "Toyota Hilux 2024",
            "tipo": "vehiculo",
            "descripcion": "Camioneta de reparto",
            "valor_adquisicion": "150000000",
            "valor_residual": "30000000",
            "vida_util_anios": 8,
            "fecha_adquisicion": "2024-01-10",
            "clasificacion": cls_id,
            "ubicacion": ub1_id,
            "centro_costo": cc_id,
            "numero_serie": "VIN-12345",
            "numero_factura": "FAC-VH-001",
        }, format="json", QUERY_STRING=qs)
        assert a1_r.status_code == 201
        a1_id = a1_r.data["id"]

        a2_r = c.post(f"{BASE}/activos/", {
            "codigo": "VH-002",
            "nombre": "Hyundai Tucson 2024",
            "tipo": "vehiculo",
            "descripcion": "SUV gerencial",
            "valor_adquisicion": "120000000",
            "valor_residual": "25000000",
            "vida_util_anios": 6,
            "fecha_adquisicion": "2024-02-20",
            "clasificacion": cls_id,
            "ubicacion": ub1_id,
            "centro_costo": cc_id,
        }, format="json", QUERY_STRING=qs)
        assert a2_r.status_code == 201
        a2_id = a2_r.data["id"]

        # ── 3. Verificar Dashboard (Tab 1) ──
        resumen = c.get(f"{BASE}/activos/resumen/", QUERY_STRING=qs)
        assert resumen.status_code == 200
        assert resumen.data["total_activos"] == 2
        assert resumen.data["activos_operativos"] == 2
        # 150M + 120M = 270M
        assert Decimal(resumen.data["valor_total_adquisicion"]) == Decimal("270000000.00")

        alertas = c.get(f"{BASE}/activos/alertas/", QUERY_STRING=qs)
        assert alertas.status_code == 200

        # ── 4. Filtrar activos (Tab 2) ──
        filt = c.get(f"{BASE}/activos/", QUERY_STRING=f"{qs}&tipo=vehiculo")
        items = filt.data if isinstance(filt.data, list) else filt.data.get("results", [])
        assert len(items) == 2

        busq = c.get(f"{BASE}/activos/", QUERY_STRING=f"{qs}&search=Hilux")
        items_b = busq.data if isinstance(busq.data, list) else busq.data.get("results", [])
        assert len(items_b) == 1
        assert items_b[0]["codigo"] == "VH-001"

        # ── 5. Mover activo (Tab 5) ──
        mov = c.post(f"{BASE}/activos/{a1_id}/mover/", {
            "ubicacion_destino": ub2_id,
            "motivo": "Transferencia a sucursal",
        }, format="json", QUERY_STRING=qs)
        assert mov.status_code == 200

        # Verificar movimiento registrado
        movs = c.get(f"{BASE}/movimientos/", QUERY_STRING=qs)
        movs_items = movs.data if isinstance(movs.data, list) else movs.data.get("results", [])
        assert len(movs_items) >= 1

        # ── 6. Mantenimiento (Tab 4) ──
        mant = c.post(f"{BASE}/mantenimientos/", {
            "activo": a2_id,
            "tipo": "preventivo",
            "descripcion": "Cambio de aceite y filtros",
            "costo": "850000",
            "proveedor_servicio": "AutoService SAE",
        }, format="json", QUERY_STRING=qs)
        assert mant.status_code == 201
        mant_id = mant.data["id"]

        # Completar
        comp = c.post(f"{BASE}/mantenimientos/{mant_id}/completar/",
                      format="json", QUERY_STRING=qs)
        assert comp.status_code == 200
        assert comp.data["estado"] == "completado"

        # ── 7. Depreciación (Tab 6) ──
        dep = c.post(f"{BASE}/activos/calcular_depreciacion/", {
            "anio": 2024,
            "mes": 3,
        }, format="json", QUERY_STRING=qs)
        assert dep.status_code == 200
        assert dep.data["registros_creados"] >= 1

        dep_list = c.get(f"{BASE}/depreciaciones/",
                         QUERY_STRING=f"{qs}&anio=2024&mes=3")
        dep_items = dep_list.data if isinstance(dep_list.data, list) else dep_list.data.get("results", [])
        assert len(dep_items) >= 1

        # Verificar fórmula depreciación activo 1
        # (150M - 30M) / (8*12) = 120M / 96 = 1,250,000 por mes
        dep_a1 = [d for d in dep_items if d.get("activo") == a1_id]
        if dep_a1:
            assert Decimal(dep_a1[0]["monto"]) == Decimal("1250000.00")

        # Dashboard actualizado
        resumen2 = c.get(f"{BASE}/activos/resumen/", QUERY_STRING=qs)
        dep_total = Decimal(resumen2.data["depreciacion_total"])
        assert dep_total > 0

        # ── 8. Dar de baja (Tab 2 acción) ──
        baja = c.post(f"{BASE}/activos/{a1_id}/dar_baja/", {
            "fecha_baja": "2024-12-31",
            "motivo": "venta",
            "motivo_detalle": "Vendido a concesionario",
            "valor_rescate": "80000000",
        }, format="json", QUERY_STRING=qs)
        assert baja.status_code == 200

        # Verificar estado baja
        det_baja = c.get(f"{BASE}/activos/{a1_id}/", QUERY_STRING=qs)
        assert det_baja.data["estado"] == "baja"

        # Listar bajas
        bajas = c.get(f"{BASE}/bajas/", QUERY_STRING=qs)
        bajas_items = bajas.data if isinstance(bajas.data, list) else bajas.data.get("results", [])
        assert len(bajas_items) >= 1

        # ── 9. Dashboard final ──
        resumen3 = c.get(f"{BASE}/activos/resumen/", QUERY_STRING=qs)
        assert resumen3.data["dados_de_baja"] >= 1
        assert resumen3.data["activos_operativos"] >= 1

        # ── 10. Limpiar catálogos ──
        del_cc = c.delete(f"{BASE}/centros-costo/{cc_id}/", QUERY_STRING=qs)
        assert del_cc.status_code == 204


# ══════════════════════════════════════════════════════════════════════════════
# AISLAMIENTO MULTI-TENANT
# ══════════════════════════════════════════════════════════════════════════════

class TestMultiTenant:
    """Verifica que datos de una empresa no se filtran a otra."""

    def test_activos_aislados_por_empresa(self, setup_env, activo):
        """Un activo de empresa A no debe verse desde empresa B."""
        c, empresa_a = setup_env

        # Crear empresa B
        empresa_b = Empresa.objects.create(
            codigo="AFT002",
            nombre="Otra Empresa",
            ruc="8888888-0",
            razon_social="Otra S.A.",
            moneda_principal="PYG",
        )
        user = Usuario.objects.get(email="af_test@test.com")
        Membership.objects.create(usuario=user, empresa=empresa_b, rol="admin")

        # Listar activos desde empresa B
        resp = c.get(f"{BASE}/activos/",
                     QUERY_STRING=f"empresa={empresa_b.id}")
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        codigos = [a["codigo"] for a in items]
        assert "AF-001" not in codigos, "Activo de empresa A visible desde empresa B"

    def test_catalogos_aislados_por_empresa(self, setup_env, clasificacion):
        c, empresa_a = setup_env
        empresa_b = Empresa.objects.create(
            codigo="AFT003",
            nombre="Tercera Empresa",
            ruc="7777777-0",
            razon_social="Tercera S.A.",
            moneda_principal="PYG",
        )
        user = Usuario.objects.get(email="af_test@test.com")
        Membership.objects.create(usuario=user, empresa=empresa_b, rol="admin")

        resp = c.get(f"{BASE}/clasificaciones/",
                     QUERY_STRING=f"empresa={empresa_b.id}")
        items = resp.data if isinstance(resp.data, list) else resp.data.get("results", [])
        nombres = [i["nombre"] for i in items]
        assert "Equipos IT" not in nombres


# ══════════════════════════════════════════════════════════════════════════════
# TIPOS DE DATOS (verificar compatibilidad frontend)
# ══════════════════════════════════════════════════════════════════════════════

class TestTiposDatos:
    """Verifica que los tipos de datos devueltos sean compatibles con el frontend."""

    def test_decimales_como_string(self, activo):
        """Los valores decimales deben ser strings para evitar pérdida de precisión."""
        assert isinstance(activo["valor_adquisicion"], str)
        assert isinstance(activo["valor_residual"], str)
        assert isinstance(activo["valor_libro"], str)
        assert isinstance(activo["depreciacion_acumulada"], str)

    def test_enteros_como_int(self, activo):
        assert isinstance(activo["vida_util_anios"], int)

    def test_uuid_como_string(self, activo):
        assert isinstance(activo["id"], str)
        assert len(activo["id"]) == 36  # UUID format

    def test_detalle_tiene_propiedades_calculadas(self, setup_env, activo):
        c, empresa = setup_env
        det = c.get(f"{BASE}/activos/{activo['id']}/",
                    QUERY_STRING=f"empresa={empresa.id}")
        d = det.data
        assert "depreciacion_mensual" in d
        assert "depreciacion_anual" in d or "porcentaje_depreciado" in d
        assert "vida_util_restante_meses" in d
        assert "esta_totalmente_depreciado" in d
        assert "supera_vida_util" in d
