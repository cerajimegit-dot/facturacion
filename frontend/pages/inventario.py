"""Inventario management page."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results, fmt


def render():
    st.header("🏭 Inventario")

    tab_stock, tab_mov, tab_almacenes = st.tabs(["📦 Stock", "🔄 Movimientos", "🏢 Almacenes"])

    # ── Stock ─────────────────────────────────────────────────────────────────
    with tab_stock:
        data, err = api.list_stock()
        if err:
            st.error(f"Error: {err}")
        else:
            stock_list = results(data)
            if not stock_list:
                st.info("No hay registros de stock. Registra movimientos de entrada para crear stock.")
            else:
                df = pd.DataFrame(stock_list)
                display_cols = [c for c in ["producto_sku", "producto_nombre", "almacen_nombre", "cantidad", "stock_minimo", "ubicacion"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)
                st.caption(f"Total: {len(stock_list)} registros")

    # ── Movimientos ───────────────────────────────────────────────────────────
    with tab_mov:
        mov_data, mov_err = api.list_movimientos()
        if mov_err:
            st.error(f"Error: {mov_err}")
        else:
            movs = results(mov_data)
            if movs:
                df = pd.DataFrame(movs)
                display_cols = [c for c in ["producto_sku", "almacen_codigo", "tipo", "cantidad", "referencia", "created_at"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)
            else:
                st.info("No hay movimientos registrados.")

        st.divider()
        st.subheader("Registrar Movimiento")

        prods_data, _ = api.list_productos()
        prods = results(prods_data)
        alm_data, _ = api.list_almacenes()
        alms = results(alm_data)

        if not prods:
            st.warning("Necesitas al menos un producto para registrar movimientos.")
        elif not alms:
            st.warning("Necesitas al menos un almacén. Puedes crearlo desde la pestaña 'Almacenes'.")
        else:
            with st.form("new_mov"):
                col1, col2 = st.columns(2)
                with col1:
                    prod_opts = {p["id"]: f"{p.get('sku','')} - {p.get('nombre','')}" for p in prods}
                    prod_id = st.selectbox("Producto", options=list(prod_opts.keys()),
                                           format_func=lambda x: prod_opts[x])
                    tipo_mov = st.selectbox("Tipo", ["entrada", "salida", "ajuste"])
                with col2:
                    alm_opts = {a["id"]: f"{a.get('codigo','')} - {a.get('nombre','')}" for a in alms}
                    alm_id = st.selectbox("Almacen", options=list(alm_opts.keys()),
                                          format_func=lambda x: alm_opts[x])
                    cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
                referencia = st.text_input("Referencia", placeholder="OC-001, ajuste inventario, etc.")

                if st.form_submit_button("Registrar Movimiento", type="primary", use_container_width=True):
                    payload = {
                        "producto": prod_id, "almacen": alm_id,
                        "tipo": tipo_mov, "cantidad": str(cantidad),
                        "referencia": referencia,
                    }
                    result, err = api.create_movimiento(payload)
                    if err:
                        st.error(f"Error: {err}")
                    else:
                        st.success("✅ Movimiento registrado.")
                        st.rerun()

    # ── Almacenes ─────────────────────────────────────────────────────────────
    with tab_almacenes:
        alm_data2, alm_err2 = api.list_almacenes()
        if alm_err2:
            st.error(f"Error: {alm_err2}")
        else:
            almacenes = results(alm_data2)
            if almacenes:
                df = pd.DataFrame(almacenes)
                display_cols = [c for c in ["codigo", "nombre", "direccion", "activo"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)
            else:
                st.info("No hay almacenes registrados. Crea uno para gestionar inventario.")

        st.divider()
        st.subheader("Crear Almacen")
        with st.form("new_almacen"):
            col1, col2 = st.columns(2)
            with col1:
                alm_codigo = st.text_input("Codigo *", placeholder="ALM001")
                alm_nombre = st.text_input("Nombre *", placeholder="Almacen Principal")
            with col2:
                alm_dir = st.text_input("Direccion", placeholder="Calle 123")
            if st.form_submit_button("Crear Almacen", type="primary", use_container_width=True):
                if not alm_codigo or not alm_nombre:
                    st.error("Codigo y Nombre son obligatorios.")
                else:
                    payload = {"codigo": alm_codigo, "nombre": alm_nombre, "direccion": alm_dir}
                    result, err = api.create_almacen(payload)
                    if err:
                        st.error(f"Error: {err}")
                    else:
                        st.success(f"✅ Almacen **{alm_nombre}** creado.")
                        st.rerun()
