"""Main Streamlit application — Facturación Multi-Empresa."""
import streamlit as st
import session_manager

st.set_page_config(
    page_title="Facturación",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Optimizar visualización del sidebar ───────────────────────────────────────
st.markdown("""
    <style>
    /* Ocultar el contenedor envolvente pero mantener la navegación visible */
    [data-testid="stSidebarNav"] {
        margin: 0 !important;
        padding: 0 !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ── Session state defaults ────────────────────────────────────────────────────
for key, default in {
    "access_token": None,
    "refresh_token": None,
    "user": None,
    "empresa_activa": None,
    "page": "dashboard",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Restaurar sesión guardada si existe ───────────────────────────────────────
if not st.session_state["access_token"]:
    session_manager.verify_and_restore_session()

# ── Imports ───────────────────────────────────────────────────────────────────
from pages import login as pg_login
from pages import dashboard as pg_dashboard
from pages import empresas as pg_empresas
from pages import usuarios as pg_usuarios
from pages import clientes as pg_clientes
from pages import productos as pg_productos
from pages import inventario as pg_inventario
from pages import ventas as pg_ventas
from pages import cobros as pg_cobros
from pages import compras as pg_compras
from pages import gastos_dashboard as pg_gastos_dashboard
from pages import pagos as pg_pagos
from pages import presupuestos as pg_presupuestos
from pages import importacion as pg_importacion
from pages import reportes as pg_reportes
from pages import auditoria as pg_auditoria
from pages import contabilidad as pg_contabilidad


def logout():
    session_manager.logout_and_clear()
    st.session_state["page"] = "dashboard"
    st.session_state.pop("modulos_permitidos", None)
    st.session_state.pop("_permisos_empresa", None)
    st.session_state.pop("user_rol_actual", None)


# ── Not logged in → show login ────────────────────────────────────────────────
if not st.session_state["access_token"]:
    pg_login.render()
    st.stop()

# ── Menu items definition ─────────────────────────────────────────────────────
menu_items = {
    "dashboard": "📈 Dashboard",
    "empresas": "🏢 Empresas",
    "usuarios": "👥 Usuarios",
    "clientes": "👥 Clientes",
    "productos": "📦 Productos",
    "inventario": "🏭 Inventario",
    "ventas": "🧾 Ventas",
    "cobros": "💳 Cobros Parciales",
    "compras": "🛒 Compras",
    "gastos_dashboard": "📊 Dashboard Gastos",
    "presupuestos": "📋 Presupuestos",
    "pagos": "💰 Pagos",
    "contabilidad": "📋 Contabilidad",
    "importacion": "📥 Importación Excel",
    "reportes": "📊 Reportes",
    "auditoria": "🔍 Auditoría",
}

# ── Sidebar navigation ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Facturación")
    user = st.session_state.get("user") or {}
    st.caption(f"👤 {user.get('email', '')}")

    empresa = st.session_state.get("empresa_activa")
    if empresa:
        st.info(f"🏢 {empresa.get('nombre', empresa.get('codigo', ''))}")

    st.divider()

    # Obtener permisos del usuario
    import api_client as _api
    if "modulos_permitidos" not in st.session_state or st.session_state.get("_permisos_empresa") != (empresa or {}).get("id"):
        permisos_data, permisos_err = _api.get_mis_permisos()
        if permisos_err and "token" in str(permisos_err).lower():
            # Token inválido/expirado — forzar re-login
            logout()
            st.rerun()
        if permisos_data:
            st.session_state["modulos_permitidos"] = permisos_data.get("modulos_permitidos", [])
            st.session_state["user_rol_actual"] = permisos_data.get("rol", user.get("rol", ""))
        else:
            st.session_state["modulos_permitidos"] = list(menu_items.keys())
            st.session_state["user_rol_actual"] = user.get("rol", "vendedor")
        st.session_state["_permisos_empresa"] = (empresa or {}).get("id")

    modulos_permitidos = st.session_state.get("modulos_permitidos", list(menu_items.keys()))
    user_rol = st.session_state.get("user_rol_actual", user.get("rol", ""))

    # Admin siempre ve todo
    if user_rol == "admin":
        visible_items = menu_items
    else:
        visible_items = {k: v for k, v in menu_items.items() if k in modulos_permitidos}

    for key, label in visible_items.items():
        if st.button(label, key=f"nav_{key}", use_container_width=True,
                     type="primary" if st.session_state["page"] == key else "secondary"):
            st.session_state["page"] = key
            st.rerun()

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚪 Cerrar Sesión", use_container_width=True):
            logout()
            st.rerun()
    with col2:
        if st.button("🗑️ Olvidar Sesión", use_container_width=True, help="Elimina la sesión guardada"):
            session_manager.clear_session()
            st.toast("✅ Sesión guardada eliminada")
            st.rerun()

# ── Check empresa selected ────────────────────────────────────────────────────
needs_empresa = st.session_state["page"] not in ("empresas", "dashboard")
if needs_empresa and not st.session_state.get("empresa_activa"):
    st.warning("⚠️ Selecciona una empresa primero en la sección **Empresas**.")
    pg_empresas.render()
    st.stop()

# ── Page router ───────────────────────────────────────────────────────────────
page_map = {
    "dashboard": pg_dashboard,
    "empresas": pg_empresas,
    "usuarios": pg_usuarios,
    "clientes": pg_clientes,
    "productos": pg_productos,
    "inventario": pg_inventario,
    "ventas": pg_ventas,
    "cobros": pg_cobros,
    "compras": pg_compras,
    "gastos_dashboard": pg_gastos_dashboard,
    "presupuestos": pg_presupuestos,
    "pagos": pg_pagos,
    "contabilidad": pg_contabilidad,
    "importacion": pg_importacion,
    "reportes": pg_reportes,
    "auditoria": pg_auditoria,
}

current = st.session_state.get("page", "dashboard")

# ── Access control check ──────────────────────────────────────────────────────
if current not in ("dashboard", "empresas") and user_rol != "admin":
    if current not in modulos_permitidos:
        st.error("🚫 No tenés acceso a este módulo. Contactá al administrador.")
        st.stop()

module = page_map.get(current, pg_dashboard)
module.render()
