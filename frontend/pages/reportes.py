"""Reportes page with charts and export."""
import streamlit as st
import pandas as pd
import plotly.express as px
import api_client as api
from helpers import results, fmt
from datetime import date, timedelta


def render():
    st.header("📊 Reportes")

    tab_ventas, tab_cxc = st.tabs(["🧾 Reporte de Ventas", "💳 Aging CxC"])

    # ── Reporte Ventas ────────────────────────────────────────────────────────
    with tab_ventas:
        col1, col2 = st.columns(2)
        with col1:
            fecha_desde = st.date_input("Desde", value=date.today() - timedelta(days=30), key="rv_desde")
        with col2:
            fecha_hasta = st.date_input("Hasta", value=date.today(), key="rv_hasta")

        if st.button("📈 Generar Reporte de Ventas", type="primary", use_container_width=True):
            with st.spinner("Generando reporte..."):
                data, err = api.get_reporte_ventas(str(fecha_desde), str(fecha_hasta))

            if err:
                st.error(f"Error: {err}")
            elif data:
                # API returns: resumen{total_ventas, total_impuestos, total_cobrado, total_pendiente, cantidad}
                #              por_estado[{estado, total, cantidad}]
                #              por_mes[{mes, total, cantidad}]
                resumen = data.get("resumen", {})
                if resumen:
                    c1, c2, c3, c4 = st.columns(4)
                    with c1:
                        st.metric("Total Ventas", fmt(resumen.get('total_ventas', 0), '₲ '))
                    with c2:
                        st.metric("Cantidad", str(resumen.get('cantidad', 0)))
                    with c3:
                        st.metric("Cobrado", fmt(resumen.get('total_cobrado', 0), '₲ '))
                    with c4:
                        st.metric("Pendiente", fmt(resumen.get('total_pendiente', 0), '₲ '))

                por_estado = data.get("por_estado", [])
                if por_estado:
                    st.divider()
                    st.subheader("Por Estado")
                    df = pd.DataFrame(por_estado)
                    st.dataframe(df, use_container_width=True, hide_index=True)

                por_mes = data.get("por_mes", [])
                if por_mes:
                    st.divider()
                    st.subheader("Por Mes")
                    df = pd.DataFrame(por_mes)
                    if "mes" in df.columns and "total" in df.columns:
                        df["total"] = df["total"].apply(lambda x: float(x) if x else 0)
                        fig = px.bar(df, x="mes", y="total", text="cantidad",
                                     color_discrete_sequence=["#1E88E5"], title="Ventas por Mes")
                        st.plotly_chart(fig, use_container_width=True)

                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Descargar CSV", csv, "reporte_ventas.csv", "text/csv",
                                       use_container_width=True)
            else:
                st.info("No hay datos disponibles.")

    # ── Aging CxC ─────────────────────────────────────────────────────────────
    with tab_cxc:
        if st.button("📈 Generar Reporte CxC", type="primary", use_container_width=True):
            with st.spinner("Generando reporte..."):
                data, err = api.get_reporte_cxc()

            if err:
                st.error(f"Error: {err}")
            elif data:
                # API returns: corriente{total,cantidad}, 1_30_dias, 31_60_dias, 61_90_dias, mas_90_dias, por_cliente[]
                st.subheader("Aging Summary")
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1:
                    st.metric("Corriente", fmt(data.get('corriente', {}).get('total', 0), '₲ '))
                with c2:
                    st.metric("1-30 dias", fmt(data.get('1_30_dias', {}).get('total', 0), '₲ '))
                with c3:
                    st.metric("31-60 dias", fmt(data.get('31_60_dias', {}).get('total', 0), '₲ '))
                with c4:
                    st.metric("61-90 dias", fmt(data.get('61_90_dias', {}).get('total', 0), '₲ '))
                with c5:
                    st.metric(">90 dias", fmt(data.get('mas_90_dias', {}).get('total', 0), '₲ '))

                por_cliente = data.get("por_cliente", [])
                if por_cliente:
                    st.divider()
                    st.subheader("Por Cliente")
                    df = pd.DataFrame(por_cliente)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Descargar CSV", csv, "reporte_cxc.csv", "text/csv",
                                       use_container_width=True)
                else:
                    st.info("No hay cuentas por cobrar por cliente.")
            else:
                st.info("No hay datos disponibles.")
