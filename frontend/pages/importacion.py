"""Excel import management page."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results


def render():
    st.header("📥 Importacion desde Excel")

    tab_upload, tab_jobs = st.tabs(["📤 Subir Archivo", "📋 Trabajos de Importacion"])

    # ── Upload ────────────────────────────────────────────────────────────────
    with tab_upload:
        st.markdown("""
        ### Formatos soportados
        - **Clientes:** columnas `nombre`, `ruc`, `telefono`, `email`, `direccion_facturacion`, `tipo_cliente`
        - **Productos:** columnas `sku`, `nombre`, `precio_unitario`, `descripcion`, `categoria`, `costo`
        - **Stock:** columnas `sku`, `almacen_codigo`, `cantidad`, `ubicacion`
        - **Ventas:** columnas `numero`, `fecha`, `cliente_ruc`, `sku`, `cantidad`, `precio_unitario`
        - **Mixto:** archivo Excel con hojas llamadas `clientes`, `productos`, `stock`, `ventas`
        """)

        st.divider()

        tipo = st.selectbox("Tipo de Importacion", ["clientes", "productos", "stock", "ventas", "mixto"])
        archivo = st.file_uploader("Archivo Excel (.xlsx)", type=["xlsx", "xls"],
                                    help="Maximo 50 MB")

        if archivo:
            st.info(f"📄 **{archivo.name}** — {archivo.size / 1024:.1f} KB")

            # Preview
            try:
                if tipo == "mixto":
                    xls = pd.ExcelFile(archivo)
                    for sheet in xls.sheet_names:
                        with st.expander(f"Hoja: {sheet}"):
                            df = pd.read_excel(xls, sheet_name=sheet, nrows=10)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    df = pd.read_excel(archivo, nrows=10)
                    st.write("**Vista previa (10 filas):**")
                    st.dataframe(df, use_container_width=True, hide_index=True)
                archivo.seek(0)
            except Exception as e:
                st.warning(f"No se pudo previsualizar: {e}")
                archivo.seek(0)

            if st.button("🚀 Subir e Importar", type="primary", use_container_width=True):
                with st.spinner("Subiendo archivo..."):
                    result, err = api.upload_import(archivo, tipo)
                    if err:
                        st.error(f"Error: {err}")
                    else:
                        job_id = result.get("id")
                        st.success(f"✅ Archivo subido. Job ID: `{job_id}`")
                        st.rerun()

    # ── Jobs List ─────────────────────────────────────────────────────────────
    with tab_jobs:
        if st.button("🔄 Refrescar", key="refresh_jobs"):
            st.rerun()

        data, err = api.list_import_jobs()
        if err:
            st.error(f"Error: {err}")
        else:
            jobs = results(data)
            if not jobs:
                st.info("No hay trabajos de importacion.")
            else:
                df = pd.DataFrame(jobs)
                display_cols = [c for c in ["tipo", "estado", "total_filas", "filas_importadas", "created_at"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)

                for job in jobs:
                    estado = job.get("estado", "")
                    icon = {"completado": "✅", "error": "❌", "validado": "🔍",
                            "validando": "⏳", "importando": "⏳", "subido": "📤"}.get(estado, "⬜")

                    with st.expander(f"{icon} {job.get('tipo','')} — {estado} — {job.get('created_at', '')[:10]}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Tipo:** {job.get('tipo', '-')}")
                            st.write(f"**Estado:** {estado}")
                            st.write(f"**Filas totales:** {job.get('total_filas', '-')}")
                        with c2:
                            st.write(f"**Importadas:** {job.get('filas_importadas', '-')}")
                            st.write(f"**Creado:** {job.get('created_at', '-')}")
                            st.write(f"**Mensaje:** {job.get('mensaje', '-')}")

                        col_a, col_b, col_c = st.columns(3)
                        with col_a:
                            if estado == "subido":
                                if st.button("🔍 Validar", key=f"val_{job['id']}"):
                                    r, e = api.validar_import(job["id"])
                                    if e:
                                        st.error(str(e))
                                    else:
                                        st.success("Validacion iniciada.")
                                    st.rerun()
                        with col_b:
                            if estado == "validado":
                                if st.button("✅ Confirmar", key=f"conf_{job['id']}"):
                                    r, e = api.confirmar_import(job["id"])
                                    if e:
                                        st.error(str(e))
                                    else:
                                        st.success("Importacion iniciada.")
                                    st.rerun()
                        with col_c:
                            if estado in ("subido", "validado"):
                                if st.button("❌ Cancelar", key=f"canc_{job['id']}"):
                                    r, e = api.cancelar_import(job["id"])
                                    if e:
                                        st.error(str(e))
                                    else:
                                        st.success("Cancelado.")
                                    st.rerun()
