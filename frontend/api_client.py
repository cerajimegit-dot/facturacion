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
    
    # Better error handling
    if data and isinstance(data, dict):
        # Extract field-level errors if they exist
        errors = []
        for key, value in data.items():
            if isinstance(value, list):
                errors.append(f"{key}: {', '.join(str(v) for v in value)}")
            else:
                errors.append(f"{key}: {value}")
        if errors:
            msg = " | ".join(errors)
        else:
            msg = str(data)
    else:
        msg = str(data) if data else f"HTTP {resp.status_code}"
    
    return None, msg


def _fetch_all(url, params=None):
    """Fetch all pages from a paginated DRF endpoint."""
    all_results = []
    while url:
        resp = requests.get(url, headers=_headers(), params=params)
        data, err = _handle(resp)
        if err:
            return None, err
        if isinstance(data, dict) and 'results' in data:
            all_results.extend(data['results'])
            url = data.get('next')
            params = None  # next URL already includes query params
        elif isinstance(data, list):
            all_results.extend(data)
            url = None
        else:
            return data, None
    return all_results, None


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


def register_full(data: dict):
    """Full registration with optional empresa creation."""
    resp = requests.post(f"{API_BASE}/auth/registro/", json=data)
    return _handle(resp)


def invitar_usuario(email: str, rol: str, first_name: str = "", last_name: str = ""):
    """Invite a new user to the authenticated user's empresa."""
    data = {
        "email": email,
        "rol": rol,
        "first_name": first_name,
        "last_name": last_name,
    }
    resp = requests.post(f"{API_BASE}/auth/invitar-usuario/", json=data, headers=_headers())
    return _handle(resp)


def list_memberships(empresa_id: str):
    """List memberships for an empresa."""
    resp = requests.get(f"{API_BASE}/auth/memberships/", headers=_headers(), params={"empresa": empresa_id})
    return _handle(resp)


def update_membership(membership_id: str, data: dict):
    """Update a membership (rol, activo)."""
    resp = requests.patch(f"{API_BASE}/auth/memberships/{membership_id}/", json=data, headers=_headers())
    return _handle(resp)


def get_mis_permisos():
    """Get allowed modules for current user."""
    params = _empresa_param()
    resp = requests.get(f"{API_BASE}/auth/mis-permisos/", headers=_headers(), params=params)
    return _handle(resp)


def list_config_acceso(empresa_id: str):
    """List access configurations per role for an empresa."""
    resp = requests.get(f"{API_BASE}/auth/config-acceso/", headers=_headers(), params={"empresa": empresa_id})
    return _handle(resp)


def save_config_acceso(config_id: str = None, empresa_id: str = "", rol: str = "", modulos: list = None):
    """Create or update access configuration for a role."""
    data = {"empresa": empresa_id, "rol": rol, "modulos_permitidos": modulos or []}
    if config_id:
        resp = requests.put(f"{API_BASE}/auth/config-acceso/{config_id}/", json=data, headers=_headers())
    else:
        resp = requests.post(f"{API_BASE}/auth/config-acceso/", json=data, headers=_headers())
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


def update_empresa_logo(empresa_id: str, logo_file):
    """Upload logo file to empresa."""
    headers = _headers()
    # Remove Content-Type to let requests set it with boundary
    if 'Content-Type' in headers:
        del headers['Content-Type']
    
    files = {'logo': logo_file}
    resp = requests.patch(
        f"{API_BASE}/empresas/{empresa_id}/", 
        headers=headers, 
        files=files
    )
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
    return _fetch_all(f"{API_BASE}/productos/", params=params)


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

def update_almacen(almacen_id: str, data: dict):
    data.update(_empresa_param())
    resp = requests.put(f"{API_BASE}/inventario/almacenes/{almacen_id}/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def delete_almacen(almacen_id: str):
    resp = requests.delete(f"{API_BASE}/inventario/almacenes/{almacen_id}/", headers=_headers(), params=_empresa_param())
    return resp.ok, None if resp.ok else f"HTTP {resp.status_code}"

# ── Ventas ────────────────────────────────────────────────────────────────────

def list_ventas(estado: str = ""):
    """List ventas, optionally filtered by estado."""
    params = _empresa_param()
    if estado:
        params["estado"] = estado
    resp = requests.get(f"{API_BASE}/ventas/", headers=_headers(), params=params)
    return _handle(resp)


def get_venta(venta_id: str):
    resp = requests.get(f"{API_BASE}/ventas/{venta_id}/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def update_venta(venta_id: str, data: dict):
    """Update venta (e.g., observaciones_cobro)."""
    data.update(_empresa_param())
    resp = requests.patch(f"{API_BASE}/ventas/{venta_id}/", json=data, headers=_headers(), params=_empresa_param())
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


# ── Registros de Pago (Pagos Parciales) ──────────────────────────────────────

def create_registro_pago(data: dict):
    """Register a partial payment for an invoice."""
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/ventas/pagos/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def list_registro_pagos(**filters):
    """List payment records."""
    params = _empresa_param()
    params.update(filters)
    resp = requests.get(f"{API_BASE}/ventas/pagos/", headers=_headers(), params=params)
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

    # Handle different file types (UploadedFile or BytesIO)
    if hasattr(file, 'name'):
        filename = file.name
        file_content = file
    else:
        filename = getattr(file, 'filename', 'import.xlsx')
        file_content = file

    files = {"archivo": (filename, file_content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    data = {"tipo": tipo, "empresa": empresa.get("id", "")}
    resp = requests.post(f"{API_BASE}/importacion/upload/", headers=headers, files=files, data=data)
    return _handle(resp)


def get_import_job(job_id: str):
    resp = requests.get(f"{API_BASE}/importacion/{job_id}/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def validar_import(job_id: str):
    resp = requests.post(f"{API_BASE}/importacion/{job_id}/validar/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def confirmar_import(job_id: str):
    resp = requests.post(f"{API_BASE}/importacion/{job_id}/confirmar/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def cancelar_import(job_id: str):
    resp = requests.post(f"{API_BASE}/importacion/{job_id}/cancelar/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def get_import_reporte(job_id: str):
    resp = requests.get(f"{API_BASE}/importacion/{job_id}/reporte/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


# ── Auditoría ─────────────────────────────────────────────────────────────────


def list_auditoria():
    resp = requests.get(f"{API_BASE}/auditoria/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


# ── Presupuestos ──────────────────────────────────────────────────────────────


def list_presupuestos(estado: str = "", cliente: str = ""):
    """List presupuestos for active empresa."""
    params = _empresa_param()
    if estado:
        params["estado"] = estado
    if cliente:
        params["cliente"] = cliente
    resp = requests.get(f"{API_BASE}/presupuestos/", headers=_headers(), params=params)
    return _handle(resp)


def create_presupuesto(data: dict):
    """Create a new presupuesto."""
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/presupuestos/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def get_presupuesto(presupuesto_id: str):
    """Get presupuesto details."""
    resp = requests.get(f"{API_BASE}/presupuestos/{presupuesto_id}/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def update_presupuesto(presupuesto_id: str, data: dict):
    """Update presupuesto."""
    resp = requests.patch(f"{API_BASE}/presupuestos/{presupuesto_id}/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def delete_presupuesto(presupuesto_id: str):
    """Delete presupuesto."""
    resp = requests.delete(f"{API_BASE}/presupuestos/{presupuesto_id}/", headers=_headers(), params=_empresa_param())
    return resp.ok, None if resp.ok else f"HTTP {resp.status_code}"


def enviar_presupuesto_email(presupuesto_id: str):
    """Send presupuesto via email."""
    resp = requests.post(f"{API_BASE}/presupuestos/{presupuesto_id}/enviar_email/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def enviar_presupuesto_whatsapp(presupuesto_id: str):
    """Send presupuesto via WhatsApp."""
    resp = requests.post(f"{API_BASE}/presupuestos/{presupuesto_id}/enviar_whatsapp/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


# ── Compras (Purchases) ───────────────────────────────────────────────────────

def list_proveedores(search: str = ""):
    """List suppliers."""
    params = _empresa_param()
    if search:
        params["search"] = search
    return _fetch_all(f"{API_BASE}/compras/proveedores/", params=params)


def create_proveedor(data: dict):
    """Create a new supplier."""
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/compras/proveedores/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def get_proveedor(proveedor_id: str):
    """Get supplier details."""
    resp = requests.get(f"{API_BASE}/compras/proveedores/{proveedor_id}/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def update_proveedor(proveedor_id: str, data: dict):
    """Update supplier."""
    resp = requests.patch(f"{API_BASE}/compras/proveedores/{proveedor_id}/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def delete_proveedor(proveedor_id: str):
    """Delete supplier."""
    resp = requests.delete(f"{API_BASE}/compras/proveedores/{proveedor_id}/", headers=_headers(), params=_empresa_param())
    return resp.ok, None if resp.ok else f"HTTP {resp.status_code}"


def list_compras(estado: str = "", search: str = ""):
    """List purchases."""
    params = _empresa_param()
    if estado:
        params["estado"] = estado
    if search:
        params["search"] = search
    return _fetch_all(f"{API_BASE}/compras/compras/", params=params)


def create_compra(data: dict):
    """Create a new purchase."""
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/compras/compras/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def get_compra(compra_id: str):
    """Get purchase details."""
    resp = requests.get(f"{API_BASE}/compras/compras/{compra_id}/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def update_compra(compra_id: str, data: dict):
    """Update purchase."""
    resp = requests.patch(f"{API_BASE}/compras/compras/{compra_id}/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def delete_compra(compra_id: str):
    """Delete purchase."""
    resp = requests.delete(f"{API_BASE}/compras/compras/{compra_id}/", headers=_headers(), params=_empresa_param())
    return resp.ok, None if resp.ok else f"HTTP {resp.status_code}"


def recibir_compra(compra_id: str):
    """Receive/ingest a purchase to stock."""
    resp = requests.post(f"{API_BASE}/compras/compras/{compra_id}/recibir/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def cancelar_compra(compra_id: str):
    """Cancel a pending purchase."""
    resp = requests.post(f"{API_BASE}/compras/compras/{compra_id}/cancelar/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def resumen_mes_compras(mes: int, ano: int):
    """Get monthly purchase summary."""
    params = _empresa_param()
    params["mes"] = mes
    params["ano"] = ano
    resp = requests.get(f"{API_BASE}/compras/compras/resumen_mes/", headers=_headers(), params=params)
    return _handle(resp)


def list_categorias_gasto():
    """List expense categories."""
    resp = requests.get(f"{API_BASE}/compras/categorias-gasto/", headers=_headers())
    return _handle(resp)


def create_categoria_gasto(data: dict):
    """Create expense category."""
    resp = requests.post(f"{API_BASE}/compras/categorias-gasto/", json=data, headers=_headers())
    return _handle(resp)


def list_gastos(categoria: str = ""):
    """List expenses."""
    params = _empresa_param()
    if categoria:
        params["categoria"] = categoria
    resp = requests.get(f"{API_BASE}/compras/gastos/", headers=_headers(), params=params)
    return _handle(resp)


def create_gasto(data: dict):
    """Create a new expense."""
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/compras/gastos/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def update_gasto(gasto_id: str, data: dict):
    """Update expense."""
    resp = requests.patch(f"{API_BASE}/compras/gastos/{gasto_id}/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def delete_gasto(gasto_id: str):
    """Delete expense."""
    resp = requests.delete(f"{API_BASE}/compras/gastos/{gasto_id}/", headers=_headers(), params=_empresa_param())
    return resp.ok, None if resp.ok else f"HTTP {resp.status_code}"


def aprobar_gasto(gasto_id: str):
    """Approve an expense."""
    resp = requests.post(f"{API_BASE}/compras/gastos/{gasto_id}/aprobar/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def resumen_categoria_gastos(mes: int, ano: int):
    """Get expense summary by category."""
    params = _empresa_param()
    params["mes"] = mes
    params["ano"] = ano
    resp = requests.get(f"{API_BASE}/compras/gastos/resumen_categoria/", headers=_headers(), params=params)
    return _handle(resp)


# ── Contabilidad ──────────────────────────────────────────────────────────────

def list_plan_cuentas(condicion: str = "", search: str = ""):
    """List accounting plan accounts."""
    params = _empresa_param()
    if condicion and condicion != "todos":
        params["condicion"] = condicion
    if search:
        params["search"] = search
    return _fetch_all(f"{API_BASE}/contabilidad/plan-cuentas/", params=params)


def create_plan_cuentas(data: dict):
    """Create a new accounting account."""
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/contabilidad/plan-cuentas/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def get_plan_cuentas(cuenta_id: str):
    """Get accounting account details."""
    resp = requests.get(f"{API_BASE}/contabilidad/plan-cuentas/{cuenta_id}/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def import_plan_cuentas(file_bytes, filename: str, preview: bool = False):
    """Import accounting plan from Excel file."""
    token = st.session_state.get("access_token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    params = _empresa_param()
    if preview:
        params["preview"] = "true"
    files = {"archivo": (filename, file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    resp = requests.post(
        f"{API_BASE}/contabilidad/plan-cuentas/importar/",
        headers=headers, params=params, files=files
    )
    return _handle(resp)


def list_asientos(estado: str = "", search: str = ""):
    """List journal entries."""
    params = _empresa_param()
    if estado and estado != "todos":
        params["estado"] = estado
    if search:
        params["search"] = search
    resp = requests.get(f"{API_BASE}/contabilidad/asientos/", headers=_headers(), params=params)
    return _handle(resp)


def create_asiento(data: dict):
    """Create a new journal entry."""
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/contabilidad/asientos/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)


def get_asiento(asiento_id: str):
    """Get journal entry details."""
    resp = requests.get(f"{API_BASE}/contabilidad/asientos/{asiento_id}/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def registrar_asiento(asiento_id: str):
    """Register a journal entry."""
    resp = requests.post(f"{API_BASE}/contabilidad/asientos/{asiento_id}/registrar/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def reversar_asiento(asiento_id: str):
    """Reverse a journal entry."""
    resp = requests.post(f"{API_BASE}/contabilidad/asientos/{asiento_id}/reversar/", headers=_headers(), params=_empresa_param())
    return _handle(resp)


def list_cotizaciones_diarias(moneda: str = "", search: str = ""):
    """List daily exchange rates."""
    params = _empresa_param()
    if moneda:
        params["moneda"] = moneda
    if search:
        params["search"] = search
    resp = requests.get(f"{API_BASE}/contabilidad/cotizaciones-diarias/", headers=_headers(), params=params)
    return _handle(resp)


def get_cotizacion_del_dia(fecha: str = ""):
    """Get exchange rate for a specific date (defaults to today)."""
    params = _empresa_param()
    if fecha:
        params["fecha"] = fecha
    resp = requests.get(f"{API_BASE}/contabilidad/cotizaciones-diarias/hoy/", headers=_headers(), params=params)
    return _handle(resp)


def create_cotizacion_diaria(data: dict):
    """Create a new daily exchange rate."""
    data.update(_empresa_param())
    resp = requests.post(f"{API_BASE}/contabilidad/cotizaciones-diarias/", json=data, headers=_headers(), params=_empresa_param())
    return _handle(resp)
