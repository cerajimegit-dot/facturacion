"""Gastos Dashboard - Analytics and reporting."""
import streamlit as st
import pandas as pd
import datetime
import api_client as api
from helpers import results, fmt, notify_error, show_session_notifications


def render():
    show_session_notifications()
    st.header("📊 Dashboard de Gastos")

    # Período
    col1, col2, col3 = st.columns(3)
    with col1:
        mes = st.selectbox(
            "Mes",
            list(range(1, 13)),
            index=datetime.date.today().month - 1,
            format_func=lambda x: datetime.date(2024, x, 1).strftime("%B")
        )
    with col2:
        ano = st.number_input("Año", min_value=2020, value=datetime.date.today().year, step=1)
    with col3:
        if st.button("🔄 Actualizar", use_container_width=True):
            st.rerun()

    # KPIs
    st.subheader("📈 Indicadores del Período")

    # Obtener datos de gastos
    gastos_data, err = api.list_gastos()
    if err:
        notify_error("No se pudieron cargar los gastos", {"details": str(err)})
        gastos = []
    else:
        gastos = results(gastos_data) if gastos_data else []
        # Filtrar por mes y año
        gastos = [
            g for g in gastos
            if datetime.datetime.strptime(g.get("fecha", ""), "%Y-%m-%d").month == mes
            and datetime.datetime.strptime(g.get("fecha", ""), "%Y-%m-%d").year == ano
        ]

    # Total de gastos
    total_gastos = sum(float(g.get("monto", 0)) for g in gastos)
    gastos_aprobados = [g for g in gastos if g.get("aprobado")]
    total_aprobados = sum(float(g.get("monto", 0)) for g in gastos_aprobados)
    gastos_pendientes = [g for g in gastos if not g.get("aprobado")]
    total_pendientes = sum(float(g.get("monto", 0)) for g in gastos_pendientes)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Gastos", fmt(total_gastos, "₲"))
    with col2:
        st.metric("Aprobados", fmt(total_aprobados, "₲"), delta=f"{len(gastos_aprobados)} registros")
    with col3:
        st.metric("Pendientes", fmt(total_pendientes, "₲"), delta=f"{len(gastos_pendientes)} registros", delta_color="inverse")
    with col4:
        st.metric("Avg. por Gasto", fmt(total_gastos / len(gastos) if gastos else 0, "₲"))

    st.divider()

    # Resumen por Categoría
    st.subheader("💰 Gasto por Categoría")

    cat_data, _ = api.list_categorias_gasto()
    categorias = results(cat_data) if cat_data else []

    # Agrupar gastos por categoría
    gasto_por_categoria = {}
    for gasto in gastos:
        cat = gasto.get("categoria_nombre", "Sin Categoría")
        if cat not in gasto_por_categoria:
            gasto_por_categoria[cat] = {"total": 0, "cantidad": 0, "aprobado": 0}
        
        gasto_por_categoria[cat]["total"] += float(gasto.get("monto", 0))
        gasto_por_categoria[cat]["cantidad"] += 1
        if gasto.get("aprobado"):
            gasto_por_categoria[cat]["aprobado"] += 1

    if gasto_por_categoria:
        # Tabla de categorías
        cat_df = pd.DataFrame([
            {
                "Categoría": cat,
                "Total": fmt(data["total"], "₲"),
                "Cantidad": data["cantidad"],
                "Aprobados": data["aprobado"],
                "% Aprobado": f"{(data['aprobado'] / data['cantidad'] * 100):.0f}%"
            }
            for cat, data in sorted(gasto_por_categoria.items(), key=lambda x: x[1]["total"], reverse=True)
        ])

        st.dataframe(cat_df, use_container_width=True, hide_index=True)

        # Gráfico de gastos por categoría
        try:
            import plotly.express as px
            
            categories = list(gasto_por_categoria.keys())
            amounts = [gasto_por_categoria[c]["total"] for c in categories]

            fig = px.pie(
                values=amounts,
                names=categories,
                title="Distribución de Gastos por Categoría",
                hole=0.3
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.info("Instala plotly para ver gráficos interactivos.")
    else:
        st.info(f"📭 No hay gastos registrados para {datetime.date(ano, mes, 1).strftime('%B de %Y')}")

    st.divider()

    # Detalle de gastos
    st.subheader("📋 Detalle de Gastos")

    if gastos:
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            cat_names = [g.get("categoria_nombre") for g in gastos]
            cat_filter = st.selectbox(
                "Filtrar por Categoría",
                ["Todos"] + sorted(set(cat_names)),
                key="detail_cat_filter"
            )
        with col2:
            aprobado_filter = st.selectbox(
                "Estado de Aprobación",
                ["Todos", "Aprobados", "Pendientes"],
                key="detail_aprobado_filter"
            )

        # Aplicar filtros
        filtered_gastos = gastos
        if cat_filter != "Todos":
            filtered_gastos = [g for g in filtered_gastos if g.get("categoria_nombre") == cat_filter]
        if aprobado_filter == "Aprobados":
            filtered_gastos = [g for g in filtered_gastos if g.get("aprobado")]
        elif aprobado_filter == "Pendientes":
            filtered_gastos = [g for g in filtered_gastos if not g.get("aprobado")]

        # Tabla
        if filtered_gastos:
            df = pd.DataFrame(filtered_gastos)
            display_cols = [c for c in ["fecha", "categoria_nombre", "descripcion", "monto", "moneda", "comprobante", "aprobado"]
                           if c in df.columns]
            
            st.dataframe(
                df[display_cols] if display_cols else df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "aprobado": st.column_config.CheckboxColumn("Aprobado"),
                    "monto": st.column_config.NumberColumn("Monto", format="%.2f"),
                }
            )

            # Descarga CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Descargar CSV",
                data=csv,
                file_name=f"gastos_{ano}_{mes:02d}.csv",
                mime="text/csv"
            )
        else:
            st.info("📭 No hay gastos con los filtros seleccionados.")
    else:
        st.info(f"📭 No hay gastos registrados para {datetime.date(ano, mes, 1).strftime('%B de %Y')}")

    st.divider()

    # Estadísticas mensuales histórico
    st.subheader("📅 Histórico de Gastos")

    # Obtener datos de todos los meses
    all_gastos, _ = api.list_gastos()
    all_gastos = results(all_gastos) if all_gastos else []

    # Agrupar por mes
    gasto_por_mes = {}
    for gasto in all_gastos:
        try:
            fecha = datetime.datetime.strptime(gasto.get("fecha", ""), "%Y-%m-%d")
            mes_key = f"{fecha.year}-{fecha.month:02d}"
            if mes_key not in gasto_por_mes:
                gasto_por_mes[mes_key] = 0
            gasto_por_mes[mes_key] += float(gasto.get("monto", 0))
        except:
            pass

    if gasto_por_mes:
        # Tabla histórica
        historico_df = pd.DataFrame([
            {
                "Período": mes,
                "Total": fmt(total, "₲"),
                "Monto": total  # Para ordenamiento
            }
            for mes, total in sorted(gasto_por_mes.items(), reverse=True)
        ]).drop("Monto", axis=1)

        st.dataframe(historico_df, use_container_width=True, hide_index=True)

        # Gráfico de tendencia
        try:
            import plotly.graph_objects as go
            
            meses = sorted(gasto_por_mes.keys())
            totales = [gasto_por_mes[m] for m in meses]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=meses,
                y=totales,
                mode='lines+markers',
                name='Gastos',
                line=dict(color='#FF6B6B', width=2),
                marker=dict(size=8)
            ))

            fig.update_layout(
                title="Tendencia de Gastos Mensuales",
                xaxis_title="Período",
                yaxis_title="Total (₲)",
                hovermode='x unified',
                height=400
            )

            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            pass
    else:
        st.info("📭 No hay datos históricos de gastos.")


if __name__ == "__main__":
    render()
