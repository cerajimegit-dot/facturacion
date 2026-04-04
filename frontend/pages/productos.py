"""Productos CRUD page."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results, fmt


def render():
    st.header("📦 Productos")

    tab_list, tab_new, tab_edit, tab_cats = st.tabs(["📋 Productos", "➕ Nuevo Producto", "✏️ Editar", "🏷️ Categorías"])

    # ── List ──────────────────────────────────────────────────────────────────
    with tab_list:
        search = st.text_input("🔍 Buscar", placeholder="SKU o nombre...", key="prod_search")

        data, err = api.list_productos(search=search)
        if err:
            st.error(f"Error: {err}")
        else:
            productos = results(data)

            if not productos:
                st.info("No hay productos registrados. Crea uno en la pestaña '➕ Nuevo Producto'.")
            else:
                df = pd.DataFrame(productos)
                display_cols = [c for c in ["sku", "nombre", "tipo", "precio_unitario", "activo"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)
                st.caption(f"Total: {len(productos)} productos")

                for prod in productos:
                    with st.expander(f"**{prod.get('sku', '')}** — {prod.get('nombre', '')}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**SKU:** {prod.get('sku', '-')}")
                            st.write(f"**Tipo:** {prod.get('tipo', '-')}")
                            st.write(f"**Precio:** {fmt(prod.get('precio_unitario', 0), '₲ ')}")
                        with c2:
                            st.write(f"**Costo:** {fmt(prod.get('costo', 0), '₲ ')}")
                            st.write(f"**IVA:** {prod.get('impuesto_porcentaje', 10)}%")
                            st.write(f"**Activo:** {'✅' if prod.get('activo', True) else '❌'}")

                        if st.button("🗑️ Eliminar", key=f"del_prod_{prod['id']}"):
                            ok, e = api.delete_producto(prod["id"])
                            if ok:
                                st.success("Producto eliminado.")
                                st.rerun()
                            else:
                                st.error(f"Error: {e}")

    # ── New Product ───────────────────────────────────────────────────────────
    with tab_new:
        with st.form("new_producto"):
            col1, col2 = st.columns(2)
            with col1:
                sku = st.text_input("SKU *", placeholder="PROD001")
                nombre = st.text_input("Nombre *", placeholder="Producto de Ejemplo")
                tipo = st.selectbox("Tipo", ["producto", "servicio"])
                precio = st.number_input("Precio Unitario *", min_value=0, value=0, step=1000)
            with col2:
                costo = st.number_input("Costo", min_value=0, value=0, step=1000)
                moneda = st.selectbox("Moneda", ["PYG", "USD"])
                impuesto = st.number_input("IVA %", min_value=0.0, max_value=100.0, value=10.0, step=0.5)
                imagen_url = st.text_input("URL de Imagen", placeholder="https://...")

            descripcion = st.text_area("Descripción", placeholder="Descripción del producto...")

            if st.form_submit_button("Crear Producto", type="primary", use_container_width=True):
                if not sku or not nombre:
                    st.error("SKU y Nombre son obligatorios.")
                else:
                    payload = {
                        "sku": sku, "nombre": nombre, "tipo": tipo,
                        "precio_unitario": str(precio), "costo": str(costo),
                        "moneda": moneda, "impuesto_porcentaje": str(impuesto),
                        "imagen_url": imagen_url, "descripcion": descripcion,
                    }
                    result, err = api.create_producto(payload)
                    if err:
                        st.error(f"Error: {err}")
                    else:
                        st.success(f"✅ Producto **{nombre}** creado.")
                        st.rerun()

    # ── Edit ──────────────────────────────────────────────────────────────────
    with tab_edit:
        data, err = api.list_productos()
        if err:
            st.error(f"Error: {err}")
        else:
            productos = results(data)
            if not productos:
                st.info("No hay productos para editar.")
            else:
                producto_options = {f"{p['sku']} — {p['nombre']}": p for p in productos}
                selected_prod = st.selectbox("Selecciona Producto para Editar", options=producto_options.keys(), key="edit_prod_select")
                
                if selected_prod:
                    prod = producto_options[selected_prod]
                    
                    with st.form("edit_producto"):
                        col1, col2 = st.columns(2)
                        with col1:
                            sku = st.text_input("SKU", value=prod.get("sku", ""))
                            nombre = st.text_input("Nombre", value=prod.get("nombre", ""))
                            tipo = st.selectbox("Tipo", ["producto", "servicio"], index=0 if prod.get("tipo") == "producto" else 1)
                            precio = st.number_input("Precio Unitario", min_value=0, value=int(prod.get("precio_unitario", 0)), step=1000)
                        with col2:
                            costo = st.number_input("Costo", min_value=0, value=int(prod.get("costo", 0)), step=1000)
                            moneda = st.selectbox("Moneda", ["PYG", "USD"], index=0 if prod.get("moneda") == "PYG" else 1)
                            impuesto = st.number_input("IVA %", min_value=0.0, max_value=100.0, value=float(prod.get("impuesto_porcentaje", 10)), step=0.5)
                            imagen_url = st.text_input("URL de Imagen", value=prod.get("imagen_url", ""))

                        descripcion = st.text_area("Descripción", value=prod.get("descripcion", ""))
                        
                        activo = st.checkbox("Activo", value=prod.get("activo", True))

                        if st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True):
                            payload = {
                                "sku": sku, "nombre": nombre, "tipo": tipo,
                                "precio_unitario": str(precio), "costo": str(costo),
                                "moneda": moneda, "impuesto_porcentaje": str(impuesto),
                                "imagen_url": imagen_url, "descripcion": descripcion, "activo": activo,
                            }
                            result, err = api.update_producto(prod["id"], payload)
                            if err:
                                st.error(f"Error: {err}")
                            else:
                                st.success(f"✅ Producto **{nombre}** actualizado.")
                                st.rerun()

    # ── Categories ────────────────────────────────────────────────────────────
    with tab_cats:
        cats_data, cats_err = api.list_categorias()
        if cats_err:
            st.error(f"Error: {cats_err}")
        else:
            categorias = results(cats_data)
            if categorias:
                df = pd.DataFrame(categorias)
                display_cols = [c for c in ["nombre", "descripcion"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)
            else:
                st.info("No hay categorías.")

        with st.form("new_cat"):
            cat_nombre = st.text_input("Nombre de Categoría *")
            cat_desc = st.text_input("Descripción")
            if st.form_submit_button("Crear Categoría", use_container_width=True):
                if not cat_nombre:
                    st.error("El nombre es obligatorio.")
                else:
                    result, err = api.create_categoria({"nombre": cat_nombre, "descripcion": cat_desc})
                    if err:
                        st.error(f"Error: {err}")
                    else:
                        st.success(f"✅ Categoría **{cat_nombre}** creada.")
                        st.rerun()
