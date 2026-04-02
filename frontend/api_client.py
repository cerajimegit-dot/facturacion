"""API client for communicating with the Django backend."""
import requests
import streamlit as st

import os
API_BASE = os.environ.get('API_BASE_URL', 'http://127.0.0.1:8000/api/v1')


def _headers():
    """Return auth headers if token exists."""
    token = st.session_state.get("access_token")
    if token:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    return {"Content-Type": "application/json"}


def _empresa_param():
    """Return empresa query param dict."""
    empresa = st.session_state.get("empresa_activa")
    if empresa:
        return {"empresa": empresa["id"]}
    return {}


def _handle(resp):
    """Return (data, error) tuple."""
    try:
        data = resp.json()
    except Exception:
        data = None
    if resp.ok:
        return data, None
    msg = str(data) if data else f"HTTP {resp.status_code}"
    return None, msg


# ── Auth ──────────────────────────────────────────────────────────────────────

def login(email: str, password: str):
    resp = requests.post(f"{API_BASE}/auth/login/", json={"email": email, "password": password})
    return _handle(resp)


def refresh_token(refresh: str):
    resp = requests.post(f"{API_BASE}/auth/token/refresh/", json={"refresh": refresh})
    return _handle(resp)


def register(email: str, password: str, nombre: str, apellido: str):
    resp = requests.post(f"{API_BASE}/auth/registro/", json={
        "email": email, "password": password, "password2": password,
        "first_name": nombre, "last_name": apellido,
    })
    return _handle(resp)


def get_perfil():
    resp = requests.get(f"{API_BASE}/auth/perfil/", headers=_headers())
    return _handle(resp)


# ── Empresas ──────────────────────────────────────────────────────────────────

def list_empresas():
    resp = requests.get(f"{API_BASE}/empresas/", headers=_headers())
    return _handle(resp)


def create_empresa(data: dict):
    resp = requests.post(f"{API_BASE}/empresas/", json=data, headers=_headers())
    return _handle(resp)


def update_empresa(empresa_id: str, data: dict):
    resp = requests.put(f"{API_BASE}/empresas/{empresa_id}/", json=data, headers=_headers())
    return _handle(resp)


def delete_empresa(empresa_id: str):
    resp = requests.delete(f"{API_BASE}/empresas/{empresa_id}/", headers=_headers())
    return resp.ok, None if resp.ok else f"HTTP {resp.status_code}"


# ── Clientes ──────────────────────────────────────────────────────────────────

def list_clientes(search: str = ""):
    params = _empresa_param()
    if search:
        params["search"] = search
    resp = requests.get(f"{API_BASE}/clientes/", headers=_headers(), params=params)
    return _handle(resp)


def create_cliente(data: dict):
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/clientes/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def update_cliente(cliente_id: str, data: dict):
    resp = requests.put(f"{API_BASE}/clientes/{cliente_id}/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def delete_cliente(cliente_id: str):
    resp = requests.delete(f"{API_BASE}/clientes/{cliente_id}/", headers=_headers(), params=_empresa_param())
    return resp.ok, None if resp.ok else f"HTTP {resp.status_code}"


# ── Productos ─────────────────────────────────────────────────────────────────

def list_productos(search: str = ""):
    params = _empresa_param()
    if search:
        params["search"] = search
    resp = requests.get(f"{API_BASE}/productos/", headers=_headers(), params=params)
    return _handle(resp)


def create_producto(data: dict):
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/productos/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def update_producto(producto_id: str, data: dict):
    resp = requests.put(f"{API_BASE}/productos/{producto_id}/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def delete_producto(producto_id: str):
    resp = requests.delete(f"{API_BASE}/productos/{producto_id}/", headers=_headers(), params=_empresa_param())
    return resp.ok, None if resp.ok else f"HTTP {resp.status_code}"


# ── Categorías ────────────────────────────────────────────────────────────────

def list_categorias():
    resp = requests.get(f"{API_BASE}/productos/categorias/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def create_categoria(data: dict):
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/productos/categorias/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


# ── Inventario ────────────────────────────────────────────────────────────────

def list_stock():
    resp = requests.get(f"{API_BASE}/inventario/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def list_almacenes():
    resp = requests.get(f"{API_BASE}/inventario/almacenes/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def list_movimientos():
    resp = requests.get(f"{API_BASE}/inventario/movimientos/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def create_almacen(data: dict):
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/inventario/almacenes/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def create_movimiento(data: dict):
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/inventario/movimientos/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


# ── Ventas ────────────────────────────────────────────────────────────────────

def list_ventas():
    resp = requests.get(f"{API_BASE}/ventas/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def get_venta(venta_id: str):
    resp = requests.get(f"{API_BASE}/ventas/{venta_id}/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def create_venta(data: dict):
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/ventas/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def confirmar_venta(venta_id: str):
    resp = requests.post(f"{API_BASE}/ventas/{venta_id}/confirmar/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def anular_venta(venta_id: str):
    resp = requests.post(f"{API_BASE}/ventas/{venta_id}/anular/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def agregar_linea_venta(venta_id: str, data: dict):
    resp = requests.post(f"{API_BASE}/ventas/{venta_id}/agregar_linea/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


# ── Cotizaciones ──────────────────────────────────────────────────────────────

def list_cotizaciones():
    resp = requests.get(f"{API_BASE}/ventas/cotizaciones/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


# ── Cuentas por Cobrar ───────────────────────────────────────────────────────

def list_cuentas_por_cobrar():
    resp = requests.get(f"{API_BASE}/ventas/cuentas-por-cobrar/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def get_cxc_resumen():
    resp = requests.get(f"{API_BASE}/ventas/cuentas-por-cobrar/resumen/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def get_cxc_vencidas():
    resp = requests.get(f"{API_BASE}/ventas/cuentas-por-cobrar/vencidas/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


# ── Pagos ─────────────────────────────────────────────────────────────────────

def list_pagos():
    resp = requests.get(f"{API_BASE}/pagos/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def create_pago(data: dict):
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/pagos/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def confirmar_pago(pago_id: str):
    resp = requests.post(f"{API_BASE}/pagos/{pago_id}/confirmar/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


# ── Contratos ─────────────────────────────────────────────────────────────────

def list_contratos():
    resp = requests.get(f"{API_BASE}/contratos/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def list_ordenes_servicio():
    resp = requests.get(f"{API_BASE}/contratos/ordenes-servicio/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


# ── Reportes ──────────────────────────────────────────────────────────────────

def get_dashboard():
    resp = requests.get(f"{API_BASE}/reportes/dashboard/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def get_reporte_ventas(fecha_desde: str = "", fecha_hasta: str = ""):
    params = _empresa_param()
    if fecha_desde:
        params["fecha_desde"] = fecha_desde
    if fecha_hasta:
        params["fecha_hasta"] = fecha_hasta
    resp = requests.get(f"{API_BASE}/reportes/ventas/", headers=_headers(), params=params)
    return _handle(resp)


def get_reporte_cxc():
    resp = requests.get(f"{API_BASE}/reportes/cuentas-por-cobrar/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


# ── Importación ───────────────────────────────────────────────────────────────

def list_import_jobs():
    resp = requests.get(f"{API_BASE}/importacion/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def upload_import(file, tipo: str):
    empresa = st.session_state.get("empresa_activa", {})
    token = st.session_state.get("access_token", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    files = {"archivo": (file.name, file, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    data = {"tipo": tipo, "empresa": empresa.get("id", "")}
    resp = requests.post(f"{API_BASE}/importacion/upload/", headers=headers, files=files, data=data)
    return _handle(resp)


def validar_import(job_id: str):
    resp = requests.post(f"{API_BASE}/importacion/{job_id}/validar/", headers=_headers())
    return _handle(resp)


def confirmar_import(job_id: str):
    resp = requests.post(f"{API_BASE}/importacion/{job_id}/confirmar/", headers=_headers())
    return _handle(resp)


def cancelar_import(job_id: str):
    resp = requests.post(f"{API_BASE}/importacion/{job_id}/cancelar/", headers=_headers())
    return _handle(resp)


def get_import_reporte(job_id: str):
    resp = requests.get(f"{API_BASE}/importacion/{job_id}/reporte/", headers=_headers())
    return _handle(resp)


# ── Auditoría ─────────────────────────────────────────────────────────────────

def list_auditoria():
    resp = requests.get(f"{API_BASE}/auditoria/", headers=_headers(), params=_empresa_param())
    return _handle(resp)
