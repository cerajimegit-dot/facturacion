"""Test exhaustivo de endpoints de Activos Fijos — tipos de dato y edge cases."""
import requests
import json
import sys

base = 'http://localhost:8000'
s = requests.Session()
ERRORS = []

# IDs globales — None si la creación falla
cid = uid1 = uid2 = ccid = afid1 = afid2 = mantid1 = mantid2 = None


def check(name, resp, expected_status=200, check_fn=None):
    ok = resp.status_code == expected_status
    prefix = "✅" if ok else "❌"
    print(f"  {prefix} {name}: {resp.status_code} (esperado {expected_status})")
    if not ok:
        ERRORS.append(f"{name}: got {resp.status_code}, expected {expected_status} — {resp.text[:200]}")
    data = None
    if resp.status_code in (200, 201):
        try:
            data = resp.json()
        except Exception:
            pass
    if ok and check_fn and data:
        try:
            check_fn(data)
        except Exception as e:
            ERRORS.append(f"{name} check_fn: {e}")
            print(f"    ❌ Validación: {e}")
    return ok, data


def assert_type(data, key, expected_type, label=""):
    val = data.get(key)
    if val is not None and not isinstance(val, expected_type if isinstance(expected_type, tuple) else (expected_type,)):
        tname = expected_type.__name__ if not isinstance(expected_type, tuple) else str(expected_type)
        msg = f"{label}.{key}: esperado {tname}, got {type(val).__name__} = {repr(val)}"
        ERRORS.append(msg)
        print(f"    ⚠️ {msg}")


def assert_decimal_str(data, key, label=""):
    """DRF devuelve Decimals como strings. Verificar que sean convertibles a float."""
    val = data.get(key)
    if val is not None:
        try:
            float(val)
        except (ValueError, TypeError):
            msg = f"{label}.{key}: no es numeric convertible: {repr(val)}"
            ERRORS.append(msg)
            print(f"    ⚠️ {msg}")


# ─── Login ────────────────────────────────────────────────────────────────────
print("=" * 60)
print("TEST EXHAUSTIVO DE ACTIVOS FIJOS")
print("=" * 60)

print("\n[1] Login")
r = s.post(f'{base}/api/v1/auth/login/', json={'email': 'admin@localhost', 'password': 'admin123'})
if r.status_code != 200:
    print(f"❌ Login falló: {r.status_code} {r.text[:200]}")
    sys.exit(1)
token = r.json()['access']
s.headers.update({'Authorization': f'Bearer {token}'})
print("  ✅ Login OK")

# Obtener empresa
r = s.get(f'{base}/api/v1/empresas/', params={})
empresas = r.json().get('results', [])
if not empresas:
    print("❌ No hay empresa. Creala primero.")
    sys.exit(1)
eid = empresas[0]['id']
p = {'empresa': eid}
print(f"  ✅ Empresa: {eid}")

# ─── Limpiar datos previos ────────────────────────────────────────────────────
print("\n[2] Limpiando datos previos...")
for ep in ['mantenimientos', 'movimientos', 'depreciaciones', 'bajas', 'activos', 'clasificaciones', 'ubicaciones', 'centros-costo']:
    try:
        resp = s.get(f'{base}/api/v1/activos-fijos/{ep}/', params=p)
        data = resp.json()
        items = data.get('results', data) if isinstance(data, dict) else data
        if isinstance(items, list):
            for item in items:
                s.delete(f'{base}/api/v1/activos-fijos/{ep}/{item["id"]}/', params=p)
    except Exception as e:
        print(f"  ⚠️ Limpieza {ep}: {e}")
print("  ✅ Datos limpiados")

# ─── Test Clasificaciones ─────────────────────────────────────────────────────
print("\n[3] Clasificaciones CRUD")

ok, cls1 = check("POST clasificacion", s.post(f'{base}/api/v1/activos-fijos/clasificaciones/', params=p,
    json={'nombre': 'Equipo IT', 'descripcion': 'Servidores y PCs', 'vida_util_default': 5}), 201)
if cls1:
    assert_type(cls1, 'id', str, 'clasificacion')
    assert_type(cls1, 'nombre', str, 'clasificacion')
    assert_type(cls1, 'vida_util_default', int, 'clasificacion')
    cid = cls1['id']

ok, cls_list = check("GET clasificaciones", s.get(f'{base}/api/v1/activos-fijos/clasificaciones/', params=p))
if cls_list:
    items = cls_list.get('results', cls_list)
    print(f"    Count: {len(items) if isinstance(items, list) else 'N/A'}")

ok, _ = check("POST clasificacion duplicada", s.post(f'{base}/api/v1/activos-fijos/clasificaciones/', params=p,
    json={'nombre': 'Equipo IT', 'descripcion': 'Dup'}), 400)

ok, _ = check("POST clasificacion sin nombre", s.post(f'{base}/api/v1/activos-fijos/clasificaciones/', params=p,
    json={'nombre': '', 'descripcion': 'x'}), 400)

# ─── Test Ubicaciones ─────────────────────────────────────────────────────────
print("\n[4] Ubicaciones CRUD")

ok, ub1 = check("POST ubicacion", s.post(f'{base}/api/v1/activos-fijos/ubicaciones/', params=p,
    json={'planta': 'Planta Baja', 'edificio': 'Principal', 'area': 'TI'}), 201)
if ub1:
    assert_type(ub1, 'id', str, 'ubicacion')
    assert_type(ub1, 'planta', str, 'ubicacion')
    assert_type(ub1, 'nombre_completo', str, 'ubicacion')
    uid1 = ub1['id']

ok, ub2 = check("POST ubicacion 2", s.post(f'{base}/api/v1/activos-fijos/ubicaciones/', params=p,
    json={'planta': 'Planta Alta', 'edificio': 'Bodega', 'area': 'Almacén'}), 201)
if ub2:
    uid2 = ub2['id']

ok, _ = check("POST ubicacion sin planta", s.post(f'{base}/api/v1/activos-fijos/ubicaciones/', params=p,
    json={'planta': '', 'edificio': 'X'}), 400)

# ─── Test Centros de Costo ────────────────────────────────────────────────────
print("\n[5] Centros de Costo CRUD")

ok, cc1 = check("POST centro costo", s.post(f'{base}/api/v1/activos-fijos/centros-costo/', params=p,
    json={'codigo': 'ADM', 'descripcion': 'Administración'}), 201)
if cc1:
    assert_type(cc1, 'id', str, 'centro_costo')
    assert_type(cc1, 'codigo', str, 'centro_costo')
    ccid = cc1['id']

ok, _ = check("POST centro costo duplicado", s.post(f'{base}/api/v1/activos-fijos/centros-costo/', params=p,
    json={'codigo': 'ADM', 'descripcion': 'Dup'}), 400)

# ─── Test Activos Fijos ──────────────────────────────────────────────────────
print("\n[6] Activos Fijos CRUD")

if not cid:
    print("  ⚠️ SKIP — no hay clasificación creada")
    ERRORS.append("Activos CRUD: skip por falta de clasificacion")
else:
    ok, af1 = check("POST activo fijo 1", s.post(f'{base}/api/v1/activos-fijos/activos/', params=p, json={
        'codigo': 'AF-001', 'nombre': 'Laptop Dell', 'tipo': 'IT',
        'descripcion': 'Laptop para dev', 'clasificacion': cid, 'ubicacion': uid1,
        'centro_costo': ccid, 'fecha_adquisicion': '2024-01-15', 'fecha_activacion': '2024-02-01',
        'valor_adquisicion': '5000.00', 'valor_residual': '500.00', 'vida_util_anios': 5,
        'estado': 'activo', 'numero_serie': 'SN-001',
    }), 201)

    if af1:
        afid1 = af1['id']
        assert_type(af1, 'id', str, 'activo')
        assert_type(af1, 'codigo', str, 'activo')
        assert_type(af1, 'nombre', str, 'activo')
        assert_type(af1, 'tipo', str, 'activo')
        assert_type(af1, 'estado', str, 'activo')
        assert_type(af1, 'vida_util_anios', int, 'activo')
        assert_type(af1, 'clasificacion_nombre', str, 'activo')
        assert_type(af1, 'ubicacion_nombre', str, 'activo')
        assert_type(af1, 'centro_costo_nombre', str, 'activo')
        assert_decimal_str(af1, 'valor_adquisicion', 'activo')
        assert_decimal_str(af1, 'valor_residual', 'activo')
        assert_decimal_str(af1, 'depreciacion_acumulada', 'activo')
        assert_decimal_str(af1, 'valor_libro', 'activo')
        assert_decimal_str(af1, 'depreciacion_mensual', 'activo')
        assert_decimal_str(af1, 'depreciacion_anual', 'activo')
        assert_decimal_str(af1, 'porcentaje_depreciado', 'activo')
        assert_type(af1, 'vida_util_restante_meses', int, 'activo')
        assert_type(af1, 'esta_totalmente_depreciado', bool, 'activo')
        assert_type(af1, 'supera_vida_util', bool, 'activo')
        print(f"    Dep mensual: {af1.get('depreciacion_mensual')}, anual: {af1.get('depreciacion_anual')}")
        print(f"    Vida restante: {af1.get('vida_util_restante_meses')} meses, Valor libro: {af1.get('valor_libro')}")
    else:
        ERRORS.append("No se pudo crear activo fijo 1")

    # Segundo activo viejo
    ok, af2 = check("POST activo viejo (vida util superada)", s.post(f'{base}/api/v1/activos-fijos/activos/', params=p, json={
        'codigo': 'AF-002', 'nombre': 'PC Antigua', 'tipo': 'IT',
        'clasificacion': cid, 'ubicacion': uid1, 'fecha_adquisicion': '2018-01-01',
        'fecha_activacion': '2018-01-01', 'valor_adquisicion': '2000.00',
        'valor_residual': '0', 'vida_util_anios': 3, 'estado': 'activo',
    }), 201)
    if af2:
        afid2 = af2['id']
        print(f"    supera_vida_util: {af2.get('supera_vida_util')}")

    # Código duplicado
    ok, _ = check("POST activo código duplicado", s.post(f'{base}/api/v1/activos-fijos/activos/', params=p,
        json={'codigo': 'AF-001', 'nombre': 'Dup', 'fecha_adquisicion': '2024-01-01',
              'valor_adquisicion': '100', 'vida_util_anios': 1}), 400)

    # GET detail + PATCH
    if afid1:
        ok, det = check("GET activo detalle", s.get(f'{base}/api/v1/activos-fijos/activos/{afid1}/', params=p))

        ok, upd = check("PATCH activo (cambiar nombre)", s.patch(f'{base}/api/v1/activos-fijos/activos/{afid1}/', params=p,
            json={'nombre': 'Laptop Dell XPS 15 Actualizada'}))
        if upd:
            assert upd['nombre'] == 'Laptop Dell XPS 15 Actualizada', "Update name failed"

    # LIST con filtros
    ok, lst = check("GET activos (sin filtro)", s.get(f'{base}/api/v1/activos-fijos/activos/', params=p))
    if lst:
        count = lst.get('count', len(lst.get('results', [])))
        print(f"    Total activos: {count}")

    ok, _ = check("GET activos (filtro estado=activo)", s.get(f'{base}/api/v1/activos-fijos/activos/', params={**p, 'estado': 'activo'}))
    ok, _ = check("GET activos (filtro tipo=IT)", s.get(f'{base}/api/v1/activos-fijos/activos/', params={**p, 'tipo': 'IT'}))
    ok, _ = check("GET activos (search=Dell)", s.get(f'{base}/api/v1/activos-fijos/activos/', params={**p, 'search': 'Dell'}))

# ─── Test Resumen ─────────────────────────────────────────────────────────────
print("\n[7] Resumen Dashboard")


def check_resumen(data):
    expected_keys = ['total_activos', 'activos_operativos', 'en_mantenimiento', 'dados_de_baja',
                     'valor_total_adquisicion', 'depreciacion_total', 'valor_libro_total',
                     'alerta_vida_util', 'mantenimientos_pendientes']
    for k in expected_keys:
        if k not in data:
            ERRORS.append(f"resumen: falta key '{k}'")
            print(f"    ⚠️ Falta key: {k}")
    for k in ['total_activos', 'activos_operativos', 'en_mantenimiento', 'dados_de_baja', 'alerta_vida_util', 'mantenimientos_pendientes']:
        assert_type(data, k, int, 'resumen')
    for k in ['valor_total_adquisicion', 'depreciacion_total', 'valor_libro_total']:
        assert_decimal_str(data, k, 'resumen')


ok, res = check("GET resumen", s.get(f'{base}/api/v1/activos-fijos/activos/resumen/', params=p), check_fn=check_resumen)
if res:
    print(f"    Resumen: {json.dumps(res, indent=2)}")

# ─── Test Alertas ─────────────────────────────────────────────────────────────
print("\n[8] Alertas")


def check_alertas(data):
    assert isinstance(data, list), f"alertas debe ser list, got {type(data)}"
    for al in data:
        for k in ['activo_id', 'codigo', 'nombre', 'tipo_alerta', 'mensaje']:
            if k not in al:
                ERRORS.append(f"alerta: falta key '{k}'")


ok, alertas = check("GET alertas", s.get(f'{base}/api/v1/activos-fijos/activos/alertas/', params=p), check_fn=check_alertas)
if alertas:
    print(f"    Alertas encontradas: {len(alertas)}")
    for a in alertas:
        print(f"      {a['tipo_alerta']}: {a['mensaje']}")

# ─── Test Depreciación ────────────────────────────────────────────────────────
print("\n[9] Calcular Depreciación")

for m in [2, 3, 4]:
    ok, dep = check(f"POST calcular dep 2024/{m:02d}", s.post(f'{base}/api/v1/activos-fijos/activos/calcular_depreciacion/',
        params=p, json={'mes': m, 'anio': 2024}))
    if dep:
        print(f"    {dep.get('mensaje', '')}: {dep.get('registros_creados', 0)} registros")

ok, dep_list = check("GET depreciaciones", s.get(f'{base}/api/v1/activos-fijos/depreciaciones/', params=p))
if dep_list:
    items = dep_list.get('results', dep_list)
    if isinstance(items, list) and items:
        d = items[0]
        assert_type(d, 'anio', int, 'depreciacion')
        assert_type(d, 'mes', int, 'depreciacion')
        assert_decimal_str(d, 'monto', 'depreciacion')
        assert_decimal_str(d, 'depreciacion_acumulada', 'depreciacion')
        assert_decimal_str(d, 'valor_libro', 'depreciacion')
        assert_type(d, 'activo_codigo', str, 'depreciacion')
        print(f"    Total registros dep: {len(items)}")
        print(f"    Ejemplo: activo={d.get('activo_codigo')}, {d.get('anio')}/{d.get('mes'):02d}, monto={d.get('monto')}")

ok, dep2 = check("POST recalcular dep 2024/02 (idempotente)", s.post(f'{base}/api/v1/activos-fijos/activos/calcular_depreciacion/',
    params=p, json={'mes': 2, 'anio': 2024}))
if dep2:
    print(f"    Registros creados (debe ser 0): {dep2.get('registros_creados', '?')}")

ok, _ = check("GET reporte depreciacion", s.get(f'{base}/api/v1/activos-fijos/depreciaciones/reporte/', params={**p, 'anio': '2024'}))

# ─── Test Mantenimiento ───────────────────────────────────────────────────────
print("\n[10] Mantenimientos")

if not afid1:
    print("  ⚠️ SKIP — no hay activo fijo 1")
    ERRORS.append("Mantenimientos: skip por falta de activo fijo")
else:
    ok, mant1_data = check("POST mantenimiento preventivo", s.post(f'{base}/api/v1/activos-fijos/mantenimientos/', params=p,
        json={'activo': afid1, 'tipo': 'preventivo', 'descripcion': 'Limpieza general', 'costo': '150.00'}), 201)
    if mant1_data:
        mantid1 = mant1_data['id']
        assert_type(mant1_data, 'id', str, 'mantenimiento')
        assert_type(mant1_data, 'tipo', str, 'mantenimiento')
        assert_type(mant1_data, 'estado', str, 'mantenimiento')
        assert_decimal_str(mant1_data, 'costo', 'mantenimiento')
        assert_type(mant1_data, 'activo_codigo', str, 'mantenimiento')
        assert_type(mant1_data, 'activo_nombre', str, 'mantenimiento')
        print(f"    Estado: {mant1_data.get('estado')} (esperado: programado)")

    ok, af_check = check("GET activo tras mantenimiento", s.get(f'{base}/api/v1/activos-fijos/activos/{afid1}/', params=p))
    if af_check:
        print(f"    Estado activo: {af_check.get('estado')} (esperado: en_mantenimiento)")

    if mantid1:
        ok, comp = check("POST completar mantenimiento", s.post(f'{base}/api/v1/activos-fijos/mantenimientos/{mantid1}/completar/', params=p))
        if comp:
            print(f"    Estado post-completar: {comp.get('estado')} (esperado: completado)")

        ok, af_check2 = check("GET activo tras completar mant", s.get(f'{base}/api/v1/activos-fijos/activos/{afid1}/', params=p))
        if af_check2:
            print(f"    Estado activo: {af_check2.get('estado')} (esperado: activo)")

    ok, mant2_data = check("POST mantenimiento correctivo", s.post(f'{base}/api/v1/activos-fijos/mantenimientos/', params=p,
        json={'activo': afid1, 'tipo': 'correctivo', 'descripcion': 'Reparación pantalla', 'costo': '500.00'}), 201)
    if mant2_data:
        mantid2 = mant2_data['id']
        ok, canc = check("POST cancelar mantenimiento", s.post(f'{base}/api/v1/activos-fijos/mantenimientos/{mantid2}/cancelar/', params=p))
        if canc:
            print(f"    Estado post-cancelar: {canc.get('estado')} (esperado: cancelado)")

    if mantid1:
        ok, _ = check("POST completar ya completado", s.post(f'{base}/api/v1/activos-fijos/mantenimientos/{mantid1}/completar/', params=p), 400)

# ─── Test Mover Activo ────────────────────────────────────────────────────────
print("\n[11] Mover Activo")

if not afid1 or not uid2:
    print("  ⚠️ SKIP — no hay activo o ubicación destino")
else:
    ok, mov = check("POST mover activo", s.post(f'{base}/api/v1/activos-fijos/activos/{afid1}/mover/', params=p,
        json={'ubicacion_destino': uid2, 'motivo': 'Reasignación'}))
    if mov:
        print(f"    Nueva ubicación: {mov.get('ubicacion_nombre')}")

    ok, movs = check("GET movimientos", s.get(f'{base}/api/v1/activos-fijos/movimientos/', params=p))
    if movs:
        items = movs.get('results', movs)
        if isinstance(items, list) and items:
            m = items[0]
            assert_type(m, 'activo_codigo', str, 'movimiento')
            assert_type(m, 'ubicacion_origen_nombre', (str, type(None)), 'movimiento')
            assert_type(m, 'ubicacion_destino_nombre', (str, type(None)), 'movimiento')
            assert_type(m, 'motivo', str, 'movimiento')
            print(f"    Movimiento: {m.get('ubicacion_origen_nombre')} → {m.get('ubicacion_destino_nombre')}")

    ok, _ = check("POST mover sin destino", s.post(f'{base}/api/v1/activos-fijos/activos/{afid1}/mover/', params=p,
        json={'motivo': 'test'}), 400)

# ─── Test Dar de Baja ─────────────────────────────────────────────────────────
print("\n[12] Dar de Baja")

if not afid2:
    print("  ⚠️ SKIP — no hay activo 2 para dar de baja")
else:
    ok, baja = check("POST dar baja activo 2", s.post(f'{base}/api/v1/activos-fijos/activos/{afid2}/dar_baja/', params=p,
        json={'fecha_baja': '2026-04-09', 'motivo': 'obsolescencia', 'motivo_detalle': 'Muy antiguo', 'valor_rescate': '50.00'}))
    if baja:
        print(f"    Baja response type: {type(baja)}")

    ok, af_baja = check("GET activo dado de baja", s.get(f'{base}/api/v1/activos-fijos/activos/{afid2}/', params=p))
    if af_baja:
        print(f"    Estado: {af_baja.get('estado')} (esperado: baja)")

    ok, bajas_list = check("GET bajas", s.get(f'{base}/api/v1/activos-fijos/bajas/', params=p))
    if bajas_list:
        items = bajas_list.get('results', [])
        print(f"    Bajas registradas: {len(items)}")

    ok, _ = check("POST dar baja repetida", s.post(f'{base}/api/v1/activos-fijos/activos/{afid2}/dar_baja/', params=p,
        json={'fecha_baja': '2026-04-09', 'motivo': 'otro'}), 400)

# ─── Test sin empresa param ───────────────────────────────────────────────────
print("\n[13] Seguridad — sin param empresa")
ok, _ = check("GET activos sin ?empresa", s.get(f'{base}/api/v1/activos-fijos/activos/'), 400)
ok, _ = check("GET clasificaciones sin ?empresa", s.get(f'{base}/api/v1/activos-fijos/clasificaciones/'), 400)

# ─── Test DELETE ──────────────────────────────────────────────────────────────
print("\n[14] DELETE")
if ccid:
    ok, _ = check("DELETE centro costo", s.delete(f'{base}/api/v1/activos-fijos/centros-costo/{ccid}/', params=p), 204)
else:
    print("  ⚠️ SKIP DELETE — no hay centro de costo")

# ─── Resumen final ────────────────────────────────────────────────────────────
print("\n" + "=" * 60)
if ERRORS:
    print(f"❌ {len(ERRORS)} ERRORES ENCONTRADOS:")
    for e in ERRORS:
        print(f"  - {e}")
else:
    print("✅ TODOS LOS TESTS PASARON — 0 ERRORES")
print("=" * 60)
