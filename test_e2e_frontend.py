"""End-to-end test simulating frontend API calls."""
import sys
import os
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')
sys.stdout.reconfigure(encoding='utf-8')
import requests
import json

API = "http://127.0.0.1:8000/api/v1"
TOKEN = None
EMPRESA_ID = None
CLIENTE_ID = None
PRODUCTO_ID = None
VENTA_ID = None


def headers():
    h = {"Content-Type": "application/json"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    return h


def check(label, resp, expected=None):
    ok = resp.ok if expected is None else resp.status_code == expected
    status = "✅" if ok else "❌"
    print(f"  {status} {label}: HTTP {resp.status_code}")
    if not ok:
        print(f"     Response: {resp.text[:300]}")
    return ok, resp


def main():
    global TOKEN, EMPRESA_ID, CLIENTE_ID, PRODUCTO_ID, VENTA_ID
    errors = 0

    import time
    unique = str(int(time.time()))[-6:]
    test_email = f"e2e{unique}@test.com"
    test_pass = "SecureE2E123!"

    print("\n=== 1. REGISTRO ===")
    ok, r = check("Registro usuario", requests.post(f"{API}/auth/registro/", json={
        "email": test_email, "first_name": "E2E", "last_name": "Test",
        "password": test_pass, "password2": test_pass,
    }), 201)
    if not ok:
        errors += 1

    print("\n=== 2. LOGIN ===")
    ok, r = check("Login con email", requests.post(f"{API}/auth/login/", json={
        "email": test_email, "password": test_pass,
    }), 200)
    if ok:
        data = r.json()
        TOKEN = data["access"]
        print(f"     User: {data.get('user', {}).get('email')}")
    else:
        errors += 1
        print("FATAL: Cannot continue without login")
        return errors

    print("\n=== 3. PERFIL ===")
    ok, r = check("Get perfil", requests.get(f"{API}/auth/perfil/", headers=headers()), 200)
    if not ok:
        errors += 1

    print("\n=== 4. EMPRESA ===")
    ok, r = check("Crear empresa", requests.post(f"{API}/empresas/", json={
        "codigo": f"E2E{unique}", "nombre": f"E2E Test Corp {unique}", "ruc": f"9999{unique}-0",
    }, headers=headers()), 201)
    if ok:
        EMPRESA_ID = r.json()["id"]
        print(f"     Empresa ID: {EMPRESA_ID}")
    else:
        errors += 1

    ok, r = check("Listar empresas", requests.get(f"{API}/empresas/", headers=headers()), 200)
    if not ok:
        errors += 1

    if not EMPRESA_ID:
        print("FATAL: Cannot continue without empresa")
        return errors

    ep = {"empresa": EMPRESA_ID}

    print("\n=== 5. CLIENTES ===")
    ok, r = check("Crear cliente", requests.post(f"{API}/clientes/", json={
        "nombre": f"Cliente E2E {unique}", "ruc": f"1234{unique}-0", "tipo_cliente": "empresa",
        "email": f"cliente{unique}@e2e.com", "telefono": "0981111222",
        "empresa": EMPRESA_ID,
    }, headers=headers(), params=ep), 201)
    if ok:
        CLIENTE_ID = r.json()["id"]
        print(f"     Cliente ID: {CLIENTE_ID}")
    else:
        errors += 1

    ok, r = check("Listar clientes", requests.get(f"{API}/clientes/", headers=headers(), params=ep), 200)
    if not ok:
        errors += 1

    print("\n=== 6. PRODUCTOS ===")
    ok, r = check("Crear producto", requests.post(f"{API}/productos/", json={
        "sku": f"E2E-P{unique}", "nombre": f"Producto E2E {unique}", "tipo": "producto",
        "precio_unitario": "50000", "costo": "30000",
        "empresa": EMPRESA_ID,
    }, headers=headers(), params=ep), 201)
    if ok:
        PRODUCTO_ID = r.json()["id"]
        print(f"     Producto ID: {PRODUCTO_ID}")
    else:
        errors += 1

    ok, r = check("Listar productos", requests.get(f"{API}/productos/", headers=headers(), params=ep), 200)
    if not ok:
        errors += 1

    print("\n=== 7. VENTAS ===")
    ok, r = check("Crear venta borrador", requests.post(f"{API}/ventas/", json={
        "numero": f"E2E-F{unique}", "cliente": CLIENTE_ID, "fecha": "2026-04-02",
        "empresa": EMPRESA_ID,
    }, headers=headers(), params=ep), 201)
    if ok:
        VENTA_ID = r.json()["id"]
        print(f"     Venta ID: {VENTA_ID}")
    else:
        errors += 1

    if VENTA_ID and PRODUCTO_ID:
        ok, r = check("Agregar línea", requests.post(
            f"{API}/ventas/{VENTA_ID}/agregar_linea/", json={
                "producto": PRODUCTO_ID, "cantidad": "3", "precio_unitario": "50000",
            }, headers=headers(), params=ep))
        if not ok:
            errors += 1

        ok, r = check("Confirmar venta", requests.post(
            f"{API}/ventas/{VENTA_ID}/confirmar/", headers=headers(), params=ep))
        if not ok:
            errors += 1

    ok, r = check("Listar ventas", requests.get(f"{API}/ventas/", headers=headers(), params=ep), 200)
    if not ok:
        errors += 1

    print("\n=== 8. CUENTAS POR COBRAR ===")
    ok, r = check("Listar CxC", requests.get(f"{API}/ventas/cuentas-por-cobrar/", headers=headers(), params=ep), 200)
    if not ok:
        errors += 1

    print("\n=== 9. PAGOS ===")
    if VENTA_ID:
        ok, r = check("Crear pago", requests.post(f"{API}/pagos/", json={
            "venta": VENTA_ID, "monto": "165000", "metodo": "efectivo",
            "fecha": "2026-04-02", "empresa": EMPRESA_ID,
        }, headers=headers(), params=ep), 201)
        if ok:
            pago_id = r.json()["id"]
            ok, r = check("Confirmar pago", requests.post(
                f"{API}/pagos/{pago_id}/confirmar/", headers=headers(), params=ep))
            if not ok:
                errors += 1
        else:
            errors += 1

    print("\n=== 10. REPORTES ===")
    ok, r = check("Dashboard", requests.get(f"{API}/reportes/dashboard/", headers=headers(), params=ep), 200)
    if not ok:
        errors += 1

    print("\n=== 11. AUDITORÍA ===")
    ok, r = check("Listar auditoría", requests.get(f"{API}/auditoria/", headers=headers(), params=ep), 200)
    if not ok:
        errors += 1

    print(f"\n{'='*50}")
    if errors == 0:
        print("✅ ALL E2E TESTS PASSED!")
    else:
        print(f"❌ {errors} TEST(S) FAILED")
    return errors


if __name__ == "__main__":
    sys.exit(main())
