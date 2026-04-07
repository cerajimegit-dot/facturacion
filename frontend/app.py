"""Main Streamlit application — Facturación Multi-Empresa."""
import streamlit as st

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


def logout():
    for k in ["access_token", "refresh_token", "user", "empresa_activa"]:
        st.session_state[k] = None
    st.session_state["page"] = "dashboard"


# ── Not logged in → show login ────────────────────────────────────────────────
if not st.session_state["access_token"]:
    pg_login.render()
    st.stop()

# ── Sidebar navigation ───────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Facturación")
    user = st.session_state.get("user") or {}
    st.caption(f"👤 {user.get('email', '')}")

    empresa = st.session_state.get("empresa_activa")
    if empresa:
        st.info(f"🏢 {empresa.get('nombre', empresa.get('codigo', ''))}")

    st.divider()

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
        "importacion": "📥 Importación Excel",
        "reportes": "📊 Reportes",
        "auditoria": "🔍 Auditoría",
    }

    for key, label in menu_items.items():
        if st.button(label, key=f"nav_{key}", use_container_width=True,
                     type="primary" if st.session_state["page"] == key else "secondary"):
            st.session_state["page"] = key
            st.rerun()

    st.divider()
    if st.button("🚪 Cerrar Sesión", use_container_width=True):
        logout()
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
    "importacion": pg_importacion,
    "reportes": pg_reportes,
    "auditoria": pg_auditoria,
}

current = st.session_state.get("page", "dashboard")
module = page_map.get(current, pg_dashboard)
module.render()
