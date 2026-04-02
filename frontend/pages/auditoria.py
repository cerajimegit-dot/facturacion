"""Auditoria log viewer page."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results


def render():
    st.header("🔍 Auditoria")

    if st.button("🔄 Refrescar", key="refresh_audit"):
        st.rerun()

    data, err = api.list_auditoria()
    if err:
        st.error(f"Error: {err}")
        return

    registros = results(data)

    if not registros:
        st.info("No hay registros de auditoria.")
        return

    df = pd.DataFrame(registros)

    # Filters
    col1, col2 = st.columns(2)
    with col1:
        if "accion" in df.columns:
            acciones = ["Todas"] + sorted(df["accion"].dropna().unique().tolist())
            accion_filter = st.selectbox("Accion", acciones)
        else:
            accion_filter = "Todas"
    with col2:
        if "modelo" in df.columns:
            modelos = ["Todos"] + sorted(df["modelo"].dropna().unique().tolist())
            modelo_filter = st.selectbox("Modelo", modelos)
        else:
            modelo_filter = "Todos"

    # Apply filters
    filtered = df.copy()
    if accion_filter != "Todas" and "accion" in filtered.columns:
        filtered = filtered[filtered["accion"] == accion_filter]
    if modelo_filter != "Todos" and "modelo" in filtered.columns:
        filtered = filtered[filtered["modelo"] == modelo_filter]

    st.divider()

    display_cols = [c for c in ["created_at", "usuario_nombre", "accion", "modelo", "objeto_id"] if c in filtered.columns]
    st.dataframe(filtered[display_cols] if display_cols else filtered, use_container_width=True, hide_index=True)
    st.caption(f"Mostrando {len(filtered)} de {len(df)} registros")

    for idx, row in filtered.head(20).iterrows():
        label = f"{row.get('created_at', '')}"
        if 'accion' in row:
            label += f" — {row['accion']}"
        if 'modelo' in row:
            label += f" {row['modelo']}"
        if 'usuario_nombre' in row:
            label += f" — {row['usuario_nombre']}"
        with st.expander(label):
            c1, c2 = st.columns(2)
            with c1:
                st.write(f"**Usuario:** {row.get('usuario_nombre', row.get('usuario', '-'))}")
                st.write(f"**Accion:** {row.get('accion', '-')}")
                st.write(f"**Modelo:** {row.get('modelo', '-')}")
            with c2:
                st.write(f"**Objeto ID:** {row.get('objeto_id', '-')}")
                st.write(f"**Empresa:** {row.get('empresa_nombre', row.get('empresa', '-'))}")

            datos_nuevos = row.get("datos_nuevos")
            if datos_nuevos and str(datos_nuevos) != "None" and datos_nuevos != "nan":
                st.write("**Datos:**")
                try:
                    st.json(datos_nuevos)
                except Exception:
                    st.code(str(datos_nuevos))
