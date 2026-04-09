"""Full diagnostic: test every API endpoint the frontend uses."""
import sys, os, time, json
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
sys.stdout.reconfigure(encoding='utf-8')
import requests

API = "http://127.0.0.1:8000/api/v1"
TOKEN = None
EMPRESA_ID = None
CLIENTE_ID = None
PRODUCTO_ID = None
VENTA_ID = None
unique = str(int(time.time()))[-6:]

def h():
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"} if TOKEN else {"Content-Type": "application/json"}

def ep():
    return {"empresa": EMPRESA_ID} if EMPRESA_ID else {}

def test(label, resp, show_body=False):
    icon = "OK" if resp.ok else "FAIL"
    print(f"  [{icon}] {label}: HTTP {resp.status_code}")
    if not resp.ok or show_body:
        try:
            print(f"       Body: {json.dumps(resp.json(), indent=2, default=str)[:500]}")
        except:
            print(f"       Body: {resp.text[:300]}")
    return resp.ok, resp

def main():
    global TOKEN, EMPRESA_ID, CLIENTE_ID, PRODUCTO_ID, VENTA_ID
    fails = []

    # 1. Register + Login
    print("\n--- AUTH ---")
    email = f"flow{unique}@test.com"
    pw = "SecureFlow123!"
    ok, r = test("Register", requests.post(f"{API}/auth/registro/", json={
        "email": email, "first_name": "Flow", "last_name": "Test",
        "password": pw, "password2": pw}))
    if not ok: fails.append("Register")

    ok, r = test("Login", requests.post(f"{API}/auth/login/", json={"email": email, "password": pw}))
    if not ok: fails.append("Login"); return fails
    TOKEN = r.json()["access"]

    ok, r = test("Perfil", requests.get(f"{API}/auth/perfil/", headers=h()))
    if not ok: fails.append("Perfil")

    # 2. Empresa
    print("\n--- EMPRESA ---")
    ok, r = test("Crear empresa", requests.post(f"{API}/empresas/", json={
        "codigo": f"FL{unique}", "nombre": f"FlowTest {unique}", "ruc": f"F{unique}-0"}, headers=h()))
    if not ok: fails.append("Crear empresa"); return fails
    EMPRESA_ID = r.json()["id"]
    print(f"       empresa_id={EMPRESA_ID}")

    ok, r = test("Listar empresas", requests.get(f"{API}/empresas/", headers=h()))
    if not ok: fails.append("Listar empresas")

    # 3. Clientes
    print("\n--- CLIENTES ---")
    ok, r = test("Listar clientes (vacío)", requests.get(f"{API}/clientes/", headers=h(), params=ep()), True)
    if not ok: fails.append("Listar clientes")

    ok, r = test("Crear cliente", requests.post(f"{API}/clientes/", json={
        "nombre": f"ClienteFlow{unique}", "ruc": f"C{unique}-0", "tipo_cliente": "empresa",
        "email": f"cli{unique}@t.com", "empresa": EMPRESA_ID}, headers=h(), params=ep()))
    if not ok: fails.append("Crear cliente")
    else: CLIENTE_ID = r.json()["id"]; print(f"       cliente_id={CLIENTE_ID}")

    ok, r = test("Listar clientes (1)", requests.get(f"{API}/clientes/", headers=h(), params=ep()))
    if not ok: fails.append("Listar clientes post-create")

    ok, r = test("Buscar cliente", requests.get(f"{API}/clientes/", headers=h(), params={**ep(), "search": "ClienteFlow"}))
    if not ok: fails.append("Buscar cliente")

    # 4. Categorías
    print("\n--- CATEGORIAS ---")
    cats_url = f"{API}/productos/categorias/"
    ok, r = test("Listar categorías", requests.get(cats_url, headers=h(), params=ep()), True)
    if not ok:
        # Try alternative URL
        cats_url2 = f"{API}/categorias/"
        ok2, r2 = test("Listar categorías (alt)", requests.get(cats_url2, headers=h(), params=ep()), True)
        if not ok2: fails.append("Listar categorías")

    # 5. Productos
    print("\n--- PRODUCTOS ---")
    ok, r = test("Listar productos", requests.get(f"{API}/productos/", headers=h(), params=ep()), True)
    if not ok: fails.append("Listar productos")

    ok, r = test("Crear producto", requests.post(f"{API}/productos/", json={
        "sku": f"SKU{unique}", "nombre": f"ProdFlow{unique}", "tipo": "producto",
        "precio_unitario": "50000", "empresa": EMPRESA_ID}, headers=h(), params=ep()))
    if not ok: fails.append("Crear producto")
    else: PRODUCTO_ID = r.json()["id"]; print(f"       producto_id={PRODUCTO_ID}")

    # 6. Inventario
    print("\n--- INVENTARIO ---")
    ok, r = test("Listar stock", requests.get(f"{API}/inventario/", headers=h(), params=ep()), True)
    if not ok: fails.append("Listar stock")

    ok, r = test("Listar almacenes", requests.get(f"{API}/inventario/almacenes/", headers=h(), params=ep()), True)
    if not ok:
        # Try creating almacen
        print("       (intentando URL alternativas...)")
        for alt in ["almacenes", "inventario/almacen"]:
            ok2, r2 = test(f"  alt: {API}/{alt}/", requests.get(f"{API}/{alt}/", headers=h(), params=ep()), True)

    ok, r = test("Listar movimientos", requests.get(f"{API}/inventario/movimientos/", headers=h(), params=ep()), True)
    if not ok: fails.append("Listar movimientos")

    # 7. Ventas
    print("\n--- VENTAS ---")
    ok, r = test("Listar ventas", requests.get(f"{API}/ventas/", headers=h(), params=ep()), True)
    if not ok: fails.append("Listar ventas")

    if CLIENTE_ID:
        ok, r = test("Crear venta", requests.post(f"{API}/ventas/", json={
            "numero": f"F{unique}", "cliente": CLIENTE_ID, "fecha": "2026-04-02",
            "empresa": EMPRESA_ID}, headers=h(), params=ep()))
        if not ok: fails.append("Crear venta")
        else:
            VENTA_ID = r.json()["id"]
            print(f"       venta_id={VENTA_ID}")

            if PRODUCTO_ID:
                ok, r = test("Agregar línea", requests.post(
                    f"{API}/ventas/{VENTA_ID}/agregar_linea/", json={
                    "producto": PRODUCTO_ID, "cantidad": "2", "precio_unitario": "50000"},
                    headers=h(), params=ep()))
                if not ok: fails.append("Agregar línea venta")

                ok, r = test("Confirmar venta", requests.post(
                    f"{API}/ventas/{VENTA_ID}/confirmar/", headers=h(), params=ep()))
                if not ok: fails.append("Confirmar venta")

    # 8. CxC
    print("\n--- CUENTAS POR COBRAR ---")
    ok, r = test("Listar CxC", requests.get(f"{API}/ventas/cuentas-por-cobrar/", headers=h(), params=ep()), True)
    if not ok: fails.append("Listar CxC")

    ok, r = test("Resumen CxC", requests.get(f"{API}/ventas/cuentas-por-cobrar/resumen/", headers=h(), params=ep()), True)
    if not ok: fails.append("Resumen CxC")

    ok, r = test("Vencidas CxC", requests.get(f"{API}/ventas/cuentas-por-cobrar/vencidas/", headers=h(), params=ep()), True)
    if not ok: fails.append("Vencidas CxC")

    # 9. Cotizaciones
    print("\n--- COTIZACIONES ---")
    ok, r = test("Listar cotizaciones", requests.get(f"{API}/ventas/cotizaciones/", headers=h(), params=ep()), True)
    if not ok: fails.append("Listar cotizaciones")

    # 10. Pagos
    print("\n--- PAGOS ---")
    ok, r = test("Listar pagos", requests.get(f"{API}/pagos/", headers=h(), params=ep()), True)
    if not ok: fails.append("Listar pagos")

    if VENTA_ID:
        ok, r = test("Crear pago", requests.post(f"{API}/pagos/", json={
            "venta": VENTA_ID, "monto": "100000", "metodo": "efectivo",
            "fecha": "2026-04-02", "empresa": EMPRESA_ID}, headers=h(), params=ep()))
        if not ok: fails.append("Crear pago")
        else:
            pago_id = r.json()["id"]
            ok, r = test("Confirmar pago", requests.post(
                f"{API}/pagos/{pago_id}/confirmar/", headers=h(), params=ep()))
            if not ok: fails.append("Confirmar pago")

    # 11. Reportes
    print("\n--- REPORTES ---")
    ok, r = test("Dashboard", requests.get(f"{API}/reportes/dashboard/", headers=h(), params=ep()), True)
    if not ok: fails.append("Dashboard")

    ok, r = test("Reporte ventas", requests.get(f"{API}/reportes/ventas/", headers=h(), params=ep()), True)
    if not ok: fails.append("Reporte ventas")

    ok, r = test("Reporte CxC", requests.get(f"{API}/reportes/cuentas-por-cobrar/", headers=h(), params=ep()), True)
    if not ok: fails.append("Reporte CxC")

    # 12. Importación
    print("\n--- IMPORTACION ---")
    ok, r = test("Listar imports", requests.get(f"{API}/importacion/", headers=h(), params=ep()), True)
    if not ok: fails.append("Listar imports")

    # 13. Auditoría
    print("\n--- AUDITORIA ---")
    ok, r = test("Listar auditoría", requests.get(f"{API}/auditoria/", headers=h(), params=ep()), True)
    if not ok: fails.append("Listar auditoría")

    # Summary
    print(f"\n{'='*60}")
    if not fails:
        print("ALL ENDPOINTS OK!")
    else:
        print(f"FAILED ({len(fails)}):")
        for f in fails:
            print(f"  - {f}")
    return fails

if __name__ == "__main__":
    f = main()
    sys.exit(len(f))
