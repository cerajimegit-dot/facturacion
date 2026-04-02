"""Dashboard page with KPIs and charts."""
import streamlit as st
import pandas as pd
import plotly.express as px
import api_client as api
from helpers import results, fmt


def render():
    st.header("📈 Dashboard")

    empresa = st.session_state.get("empresa_activa")
    if not empresa:
        st.info("Selecciona una empresa en el menu **Empresas** para ver el dashboard.")
        return

    data, err = api.get_dashboard()
    if err:
        st.error(f"Error cargando dashboard: {err}")
        return
    if not data:
        st.info("No hay datos disponibles aun.")
        return

    # ── KPI Cards ─────────────────────────────────────────────────────────────
    # API response structure:
    # ventas_mes: {total, cantidad}
    # cobros_mes: {total}
    # cuentas_por_cobrar: {total_pendiente, cantidad, total_vencido, cantidad_vencidas}
    # totales: {clientes_activos, productos_activos}
    # top_clientes_mes: [{cliente__nombre, total}]
    # moneda: str

    moneda = data.get("moneda", "PYG")
    ventas_mes = data.get("ventas_mes", {})
    cobros_mes = data.get("cobros_mes", {})
    cxc = data.get("cuentas_por_cobrar", {})
    totales = data.get("totales", {})

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            "🧾 Ventas del Mes",
            f"{ventas_mes.get('cantidad', 0)} ventas",
            f"{fmt(ventas_mes.get('total', 0), '₲ ')}"
        )
    with c2:
        st.metric("💰 Cobros del Mes", fmt(cobros_mes.get('total', 0), '₲ '))
    with c3:
        st.metric("👥 Clientes Activos", str(totales.get('clientes_activos', 0)))
    with c4:
        st.metric("📦 Productos Activos", str(totales.get('productos_activos', 0)))

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("💳 Cuentas por Cobrar")
        cxc_c1, cxc_c2 = st.columns(2)
        with cxc_c1:
            st.metric("Pendiente", fmt(cxc.get('total_pendiente', 0), '₲ '))
            st.metric("Cantidad", str(cxc.get('cantidad', 0)))
        with cxc_c2:
            st.metric("Vencido", fmt(cxc.get('total_vencido', 0), '₲ '))
            st.metric("Vencidas", str(cxc.get('cantidad_vencidas', 0)))

    with col_right:
        st.subheader("🏆 Top Clientes del Mes")
        top_clientes = data.get("top_clientes_mes", [])
        if top_clientes:
            df = pd.DataFrame(top_clientes)
            if "cliente__nombre" in df.columns:
                df = df.rename(columns={"cliente__nombre": "Cliente", "total": "Total"})
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No hay datos de clientes este mes.")

    # ── Ventas por mes chart ──────────────────────────────────────────────────
    st.divider()
    ventas_por_mes = data.get("ventas_por_mes", [])
    if ventas_por_mes:
        st.subheader("📊 Ventas por Mes")
        df = pd.DataFrame(ventas_por_mes)
        if "mes" in df.columns and "total" in df.columns:
            df["total"] = df["total"].apply(lambda x: float(x) if x else 0)
            fig = px.bar(df, x="mes", y="total", text="cantidad",
                         color_discrete_sequence=["#1E88E5"])
            fig.update_layout(xaxis_title="Mes", yaxis_title=f"Total ({moneda})")
            st.plotly_chart(fig, use_container_width=True)
