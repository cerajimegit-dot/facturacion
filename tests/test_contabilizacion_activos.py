"""
Test new contabilidad-integration features in activos_fijos.

Covers:
  - Clasificaciones with cuentas contables
  - ActivoFijo new fields: moneda, propiedad_terceros, cuentas override
  - ProcesoDepreciacion creation on depreciación
  - Exclusion of propiedad_terceros from depreciation
  - Secuencialidad enforcement
  - Asiento generation on depreciación and baja
"""
import pytest
from rest_framework.test import APIClient

from apps.usuarios.models import Usuario, Membership
from apps.empresas.models import Empresa
from apps.activos_fijos.models import (
    ClasificacionActivo, ActivoFijo, ProcesoDepreciacion,
    UbicacionActivo, CentroCosto
)
from apps.contabilidad.models import PlanCuentas, Asiento

BASE = "/api/v1/activos-fijos"


@pytest.fixture
def env(db):
    """Create user + empresa + cuentas contables; return (client, empresa, cuentas)."""
    user = Usuario.objects.create_user(
        username='ct_test', email='ct@test.com', password='Test1234!',
        first_name='CT', last_name='Tester',
    )
    empresa = Empresa.objects.create(
        codigo='CT001', nombre='CT Test Corp', ruc='8888888-0',
        razon_social='CT Test S.A.', moneda_principal='PYG',
    )
    Membership.objects.create(usuario=user, empresa=empresa, rol='admin')

    client = APIClient()
    client.force_authenticate(user=user)

    ctas = {
        'activo': PlanCuentas.objects.create(
            empresa=empresa, codigo_cuenta='161', descripcion='Bienes de Uso',
            condicion='deudora', clase='analitica',
        ),
        'dep_acum': PlanCuentas.objects.create(
            empresa=empresa, codigo_cuenta='169', descripcion='Dep. Acumulada',
            condicion='acreedora', clase='analitica',
        ),
        'gasto': PlanCuentas.objects.create(
            empresa=empresa, codigo_cuenta='541', descripcion='Gasto Depreciación',
            condicion='deudora', clase='analitica',
        ),
        'resultado': PlanCuentas.objects.create(
            empresa=empresa, codigo_cuenta='491', descripcion='Resultado Baja AF',
            condicion='acreedora', clase='analitica',
        ),
    }
    return client, empresa, ctas, user


@pytest.fixture
def qs(env):
    """Query string with empresa id."""
    _, empresa, _, _ = env
    return f"empresa={empresa.id}"


def _post(client, url, data, qs):
    return client.post(url, data, format="json", QUERY_STRING=qs)


def _get(client, url, qs):
    return client.get(url, QUERY_STRING=qs)


# ── Clasificaciones con cuentas ────────────────────────────────────────────


class TestClasificacionConCuentas:

    def test_create_with_cuentas(self, env, qs):
        c, emp, ctas, _ = env
        resp = _post(c, f"{BASE}/clasificaciones/", {
            'nombre': 'Equipos de Cómputo',
            'vida_util_default': 5,
            'cuenta_activo': str(ctas['activo'].id),
            'cuenta_depreciacion_acumulada': str(ctas['dep_acum'].id),
            'cuenta_gasto_depreciacion': str(ctas['gasto'].id),
            'cuenta_resultado_baja': str(ctas['resultado'].id),
        }, qs)
        assert resp.status_code == 201, resp.data
        d = resp.json()
        assert str(d['cuenta_activo']) == str(ctas['activo'].id)
        assert str(d['cuenta_depreciacion_acumulada']) == str(ctas['dep_acum'].id)
        assert 'Bienes de Uso' in d.get('cuenta_activo_nombre', '')

    def test_create_without_cuentas(self, env, qs):
        c, *_ = env
        resp = _post(c, f"{BASE}/clasificaciones/", {
            'nombre': 'Mobiliario', 'vida_util_default': 10,
        }, qs)
        assert resp.status_code == 201
        d = resp.json()
        assert d['cuenta_activo'] is None

    def test_list_shows_cuenta_nombres(self, env, qs):
        c, emp, ctas, _ = env
        ClasificacionActivo.objects.create(
            empresa=emp, nombre='Test', vida_util_default=5,
            cuenta_activo=ctas['activo'],
        )
        resp = _get(c, f"{BASE}/clasificaciones/", qs)
        assert resp.status_code == 200
        items = resp.json().get('results', resp.json())
        assert 'cuenta_activo_nombre' in items[0]


# ── ActivoFijo nuevos campos ──────────────────────────────────────────────


class TestActivoFijoNewFields:

    @pytest.fixture
    def cls_ub(self, env):
        _, emp, ctas, _ = env
        cls_obj = ClasificacionActivo.objects.create(
            empresa=emp, nombre='Equipos', vida_util_default=5,
            cuenta_activo=ctas['activo'],
            cuenta_depreciacion_acumulada=ctas['dep_acum'],
            cuenta_gasto_depreciacion=ctas['gasto'],
            cuenta_resultado_baja=ctas['resultado'],
        )
        ub = UbicacionActivo.objects.create(empresa=emp, planta='Oficina Central')
        return cls_obj, ub

    def _activo_payload(self, cls_obj, ub, **kw):
        base = {
            'codigo': 'AF-T-001', 'nombre': 'Test AF', 'tipo': 'IT',
            'clasificacion': str(cls_obj.id), 'ubicacion': str(ub.id),
            'valor_adquisicion': '10000000', 'valor_residual': '1000000',
            'vida_util_anios': 5, 'fecha_adquisicion': '2025-01-15',
        }
        base.update(kw)
        return base

    def test_moneda_usd(self, env, qs, cls_ub):
        c, *_ = env
        cls_obj, ub = cls_ub
        resp = _post(c, f"{BASE}/activos/", self._activo_payload(cls_obj, ub,
            codigo='AF-USD-001', moneda='USD'), qs)
        assert resp.status_code == 201, resp.data
        assert resp.json()['moneda'] == 'USD'

    def test_default_moneda_pyg(self, env, qs, cls_ub):
        c, *_ = env
        cls_obj, ub = cls_ub
        resp = _post(c, f"{BASE}/activos/", self._activo_payload(cls_obj, ub,
            codigo='AF-PYG-001'), qs)
        assert resp.status_code == 201
        assert resp.json()['moneda'] == 'PYG'

    def test_propiedad_terceros_true(self, env, qs, cls_ub):
        c, *_ = env
        cls_obj, ub = cls_ub
        resp = _post(c, f"{BASE}/activos/", self._activo_payload(cls_obj, ub,
            codigo='AF-TER-001', propiedad_terceros=True), qs)
        assert resp.status_code == 201, resp.data
        assert resp.json()['propiedad_terceros'] is True

    def test_propiedad_terceros_default_false(self, env, qs, cls_ub):
        c, *_ = env
        cls_obj, ub = cls_ub
        resp = _post(c, f"{BASE}/activos/", self._activo_payload(cls_obj, ub,
            codigo='AF-DEF-001'), qs)
        assert resp.status_code == 201
        assert resp.json()['propiedad_terceros'] is False

    def test_cuentas_override(self, env, qs, cls_ub):
        c, _, ctas, _ = env
        cls_obj, ub = cls_ub
        resp = _post(c, f"{BASE}/activos/", self._activo_payload(cls_obj, ub,
            codigo='AF-OVR-001', cuenta_activo=str(ctas['activo'].id)), qs)
        assert resp.status_code == 201, resp.data
        assert str(resp.json()['cuenta_activo']) == str(ctas['activo'].id)


# ── ProcesoDepreciacion ──────────────────────────────────────────────────


class TestProcesoDepreciacion:

    def _make_depreciable(self, emp, ctas):
        cls_obj = ClasificacionActivo.objects.create(
            empresa=emp, nombre='ClsDep', vida_util_default=5,
            cuenta_activo=ctas['activo'],
            cuenta_depreciacion_acumulada=ctas['dep_acum'],
            cuenta_gasto_depreciacion=ctas['gasto'],
        )
        ub = UbicacionActivo.objects.create(empresa=emp, planta='UbDep')
        af = ActivoFijo.objects.create(
            empresa=emp, codigo='AF-DEP-001', nombre='Test Dep',
            tipo='IT', clasificacion=cls_obj, ubicacion=ub,
            valor_adquisicion=10000000, valor_residual=1000000,
            vida_util_anios=5, fecha_adquisicion='2025-01-01',
            estado='activo',
        )
        return cls_obj, ub, af

    def test_list_procesos_empty(self, env, qs):
        c, *_ = env
        resp = _get(c, f"{BASE}/procesos-depreciacion/", qs)
        assert resp.status_code == 200

    def test_proceso_created_on_depreciacion(self, env, qs):
        c, emp, ctas, _ = env
        self._make_depreciable(emp, ctas)
        resp = _post(c, f"{BASE}/activos/calcular_depreciacion/",
                     {'anio': 2025, 'mes': 1}, qs)
        assert resp.status_code == 200, resp.data
        assert resp.json()['registros_creados'] >= 1
        proc = ProcesoDepreciacion.objects.filter(empresa=emp, anio=2025, mes=1).first()
        assert proc is not None
        assert proc.estado == 'completado'

    def test_excludes_propiedad_terceros(self, env, qs):
        c, emp, ctas, _ = env
        cls_obj = ClasificacionActivo.objects.create(
            empresa=emp, nombre='Cls3ro', vida_util_default=5,
            cuenta_activo=ctas['activo'],
            cuenta_depreciacion_acumulada=ctas['dep_acum'],
            cuenta_gasto_depreciacion=ctas['gasto'],
        )
        ub = UbicacionActivo.objects.create(empresa=emp, planta='Ub3ro')
        ActivoFijo.objects.create(
            empresa=emp, codigo='AF-PR-001', nombre='Propio',
            tipo='IT', clasificacion=cls_obj, ubicacion=ub,
            valor_adquisicion=10000000, valor_residual=1000000,
            vida_util_anios=5, fecha_adquisicion='2025-01-01',
            estado='activo', propiedad_terceros=False,
        )
        ActivoFijo.objects.create(
            empresa=emp, codigo='AF-3R-001', nombre='Tercero',
            tipo='planta', clasificacion=cls_obj, ubicacion=ub,
            valor_adquisicion=50000000, valor_residual=5000000,
            vida_util_anios=10, fecha_adquisicion='2025-01-01',
            estado='activo', propiedad_terceros=True,
        )
        resp = _post(c, f"{BASE}/activos/calcular_depreciacion/",
                     {'anio': 2025, 'mes': 1}, qs)
        assert resp.status_code == 200, resp.data
        assert resp.json()['registros_creados'] == 1


# ── Secuencialidad ───────────────────────────────────────────────────────


class TestSecuencialidad:

    def _setup_for_seq(self, emp, ctas):
        cls_obj = ClasificacionActivo.objects.create(
            empresa=emp, nombre='ClsSeq', vida_util_default=5,
            cuenta_activo=ctas['activo'],
            cuenta_depreciacion_acumulada=ctas['dep_acum'],
            cuenta_gasto_depreciacion=ctas['gasto'],
        )
        ub = UbicacionActivo.objects.create(empresa=emp, planta='UbSeq')
        ActivoFijo.objects.create(
            empresa=emp, codigo='AF-SEQ-001', nombre='Test Seq',
            tipo='IT', clasificacion=cls_obj, ubicacion=ub,
            valor_adquisicion=10000000, valor_residual=1000000,
            vida_util_anios=5, fecha_adquisicion='2025-01-01',
            estado='activo',
        )

    def test_cannot_skip_months(self, env, qs):
        c, emp, ctas, _ = env
        self._setup_for_seq(emp, ctas)

        # Jan OK (first ever)
        r1 = _post(c, f"{BASE}/activos/calcular_depreciacion/",
                   {'anio': 2025, 'mes': 1}, qs)
        assert r1.status_code == 200

        # Skip to March → fail
        r3 = _post(c, f"{BASE}/activos/calcular_depreciacion/",
                   {'anio': 2025, 'mes': 3}, qs)
        assert r3.status_code == 400, f"Expected 400, got {r3.status_code}: {r3.data}"

    def test_sequential_ok(self, env, qs):
        c, emp, ctas, _ = env
        self._setup_for_seq(emp, ctas)

        r1 = _post(c, f"{BASE}/activos/calcular_depreciacion/",
                   {'anio': 2025, 'mes': 1}, qs)
        assert r1.status_code == 200
        r2 = _post(c, f"{BASE}/activos/calcular_depreciacion/",
                   {'anio': 2025, 'mes': 2}, qs)
        assert r2.status_code == 200


# ── Asiento generation ────────────────────────────────────────────────────


class TestAsientoGeneration:

    def test_depreciacion_creates_asiento(self, env, qs):
        c, emp, ctas, _ = env
        cls_obj = ClasificacionActivo.objects.create(
            empresa=emp, nombre='ClsAsiento', vida_util_default=5,
            cuenta_activo=ctas['activo'],
            cuenta_depreciacion_acumulada=ctas['dep_acum'],
            cuenta_gasto_depreciacion=ctas['gasto'],
        )
        ub = UbicacionActivo.objects.create(empresa=emp, planta='UbAsiento')
        ActivoFijo.objects.create(
            empresa=emp, codigo='AF-ASI-001', nombre='Test Asiento',
            tipo='IT', clasificacion=cls_obj, ubicacion=ub,
            valor_adquisicion=12000000, valor_residual=0,
            vida_util_anios=5, fecha_adquisicion='2025-01-01',
            estado='activo',
        )
        initial = Asiento.objects.filter(empresa=emp).count()
        resp = _post(c, f"{BASE}/activos/calcular_depreciacion/",
                     {'anio': 2025, 'mes': 1}, qs)
        assert resp.status_code == 200
        assert Asiento.objects.filter(empresa=emp).count() > initial

    def test_baja_creates_asiento(self, env, qs):
        c, emp, ctas, _ = env
        cls_obj = ClasificacionActivo.objects.create(
            empresa=emp, nombre='ClsBaja', vida_util_default=5,
            cuenta_activo=ctas['activo'],
            cuenta_depreciacion_acumulada=ctas['dep_acum'],
            cuenta_gasto_depreciacion=ctas['gasto'],
            cuenta_resultado_baja=ctas['resultado'],
        )
        ub = UbicacionActivo.objects.create(empresa=emp, planta='UbBaja')
        af = ActivoFijo.objects.create(
            empresa=emp, codigo='AF-BAJ-001', nombre='Test Baja',
            tipo='IT', clasificacion=cls_obj, ubicacion=ub,
            valor_adquisicion=10000000, valor_residual=1000000,
            vida_util_anios=5, fecha_adquisicion='2025-01-01',
            estado='activo',
        )
        initial = Asiento.objects.filter(empresa=emp).count()
        resp = _post(c, f"{BASE}/activos/{af.id}/dar_baja/", {
            'motivo': 'Obsolescencia tecnológica',
            'fecha_baja': '2025-06-15',
        }, qs)
        assert resp.status_code == 200, resp.data
        assert Asiento.objects.filter(empresa=emp).count() > initial
