"""Productos CRUD page."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results, fmt, notify_success, notify_error, notify_info, show_session_notifications


def render():
    show_session_notifications()
    st.header("📦 Productos")

    tab_list, tab_new, tab_edit, tab_cats = st.tabs(["📋 Productos", "➕ Nuevo Producto", "✏️ Editar", "🏷️ Categorías"])

    # ── List ──────────────────────────────────────────────────────────────────
    with tab_list:
        search = st.text_input("🔍 Buscar", placeholder="SKU o nombre...", key="prod_search")

        data, err = api.list_productos(search=search)
        if err:
            notify_error("No se pudieron cargar los productos", {"details": str(err)})
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
                            st.write(f"**Moneda:** {prod.get('moneda', '-')}")
                        with c2:
                            st.write(f"**Costo:** {fmt(prod.get('costo', 0), '₲ ')}")
                            st.write(f"**IVA:** {prod.get('impuesto_porcentaje', 10)}%")
                            st.write(f"**Activo:** {'✅' if prod.get('activo', True) else '❌'}")
                        
                        if prod.get('cuenta_contable'):
                            st.write(f"**Cuenta Contable:** {prod.get('cuenta_contable')}")

                        if st.button("🗑️ Eliminar", key=f"del_prod_{prod['id']}"):
                            ok, e = api.delete_producto(prod["id"])
                            if ok:
                                notify_success(f"Producto **{prod.get('nombre')}** eliminado.")
                                st.rerun()
                            else:
                                notify_error(f"No se pudo eliminar el producto", {"details": str(e)})

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

            st.write("### Información Contable")
            cuentas_data, _ = api.list_plan_cuentas()
            cuentas = []
            if cuentas_data:
                if isinstance(cuentas_data, list):
                    cuentas = cuentas_data
                elif isinstance(cuentas_data, dict) and "results" in cuentas_data:
                    cuentas = cuentas_data["results"]
            if cuentas:
                cuenta_options = {f"{c.get('codigo_cuenta')} - {c.get('descripcion')}": c.get('id') for c in cuentas}
                cuenta_contable_id = st.selectbox("Cuenta Contable de DEBE", options=list(cuenta_options.keys()) if cuenta_options else ["Sin cuentas disponibles"])
                cuenta_contable_value = cuenta_options.get(cuenta_contable_id) if cuenta_contable_id in cuenta_options else None
            else:
                st.warning("No hay cuentas contables disponibles. Crea el plan de cuentas primero.")
                cuenta_contable_value = None

            if st.form_submit_button("Crear Producto", type="primary", use_container_width=True):
                if not sku or not nombre:
                    notify_error("SKU y Nombre son obligatorios")
                else:
                    payload = {
                        "sku": sku, "nombre": nombre, "tipo": tipo,
                        "precio_unitario": str(precio), "costo": str(costo),
                        "moneda": moneda, "impuesto_porcentaje": str(impuesto),
                        "imagen_url": imagen_url, "descripcion": descripcion,
                    }
                    if cuenta_contable_value:
                        payload["cuenta_contable"] = cuenta_contable_value
                    
                    result, err = api.create_producto(payload)
                    if err:
                        notify_error(f"No se pudo crear el producto", {"details": str(err), "payload": payload})
                    else:
                        notify_success(f"Producto **{nombre}** creado correctamente")
                        st.cache_data.clear()
                        st.cache_resource.clear()
                        import time
                        time.sleep(0.5)
                        st.rerun()

    # ── Edit ──────────────────────────────────────────────────────────────────
    with tab_edit:
        data, err = api.list_productos()
        if err:
            notify_error("No se pudieron cargar los productos para editar", {"details": str(err)})
        else:
            productos = results(data)
            if not productos:
                st.info("No hay productos para editar.")
            else:
                producto_options = {f"{p['sku']} — {p['nombre']}": p for p in productos}
                selected_prod = st.selectbox("Selecciona Producto para Editar", options=producto_options.keys(), key="edit_prod_select")
                
                if selected_prod:
                    prod = producto_options[selected_prod]
                    
                    # Show product details before form
                    with st.expander("📌 Detalles Actuales", expanded=False):
                        st.write(f"**SKU:** {prod.get('sku', '-')}")
                        st.write(f"**Nombre:** {prod.get('nombre', '-')}")
                        st.write(f"**Costo:** {prod.get('costo', '-')}")
                        st.write(f"**Descripción:** {prod.get('descripcion', '-')}")
                    
                    with st.form("edit_producto"):
                        col1, col2 = st.columns(2)
                        with col1:
                            sku = st.text_input("SKU", value=prod.get("sku", ""), disabled=True)
                            nombre = st.text_input("Nombre", value=prod.get("nombre", ""))
                            tipo = st.selectbox("Tipo", ["producto", "servicio"], index=0 if prod.get("tipo") == "producto" else 1)
                            precio = st.number_input("Precio Unitario", min_value=0, value=int(float(prod.get("precio_unitario", 0) or 0)), step=1000)
                        with col2:
                            costo = st.number_input("Costo", min_value=0, value=int(float(prod.get("costo", 0) or 0)), step=1000)
                            moneda = st.selectbox("Moneda", ["PYG", "USD"], index=0 if prod.get("moneda") == "PYG" else 1)
                            impuesto = st.number_input("IVA %", min_value=0.0, max_value=100.0, value=float(prod.get("impuesto_porcentaje", 10)), step=0.5)
                            imagen_url = st.text_input("URL de Imagen", value=prod.get("imagen_url", ""))

                        descripcion = st.text_area("Descripción", value=prod.get("descripcion", ""), height=100)
                        
                        activo = st.checkbox("Activo", value=prod.get("activo", True))
                        
                        st.write("### Información Contable")
                        cuentas_data, _ = api.list_plan_cuentas()
                        cuentas = []
                        if cuentas_data:
                            if isinstance(cuentas_data, list):
                                cuentas = cuentas_data
                            elif isinstance(cuentas_data, dict) and "results" in cuentas_data:
                                cuentas = cuentas_data["results"]
                        if cuentas:
                            cuenta_options = {f"{c.get('codigo_cuenta')} - {c.get('descripcion')}": c.get('id') for c in cuentas}
                            
                            current_cuenta_id = prod.get('cuenta_contable')
                            # Find the matching option by ID
                            current_option = None
                            if current_cuenta_id:
                                for opt, cid in cuenta_options.items():
                                    if str(cid) == str(current_cuenta_id):
                                        current_option = opt
                                        break
                            
                            # Get index or default to 0
                            options_list = list(cuenta_options.keys())
                            if current_option and current_option in options_list:
                                cuenta_index = options_list.index(current_option)
                            else:
                                cuenta_index = 0
                            
                            cuenta_contable_id = st.selectbox(
                                "Cuenta Contable de DEBE", 
                                options=options_list if options_list else ["Sin cuentas disponibles"],
                                index=cuenta_index,
                                key=f"edit_cuenta_contable_{prod.get('id', '')}"
                            )
                            cuenta_contable_value = cuenta_options.get(cuenta_contable_id)
                        else:
                            st.warning("No hay cuentas contables disponibles. Crea el plan de cuentas primero.")
                            cuenta_contable_value = prod.get('cuenta_contable')

                        submitted = st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True)
                        
                        if submitted:
                            # Validate required fields
                            if not nombre or nombre.strip() == "":
                                notify_error("El nombre del producto es obligatorio")
                            elif precio < 0 or costo < 0:
                                notify_error("Precio y costo no pueden ser negativos")
                            else:
                                # Prepare payload - DO NOT include SKU to avoid unique_together constraint
                                # SKU is immutable once created
                                payload = {
                                    "nombre": nombre.strip(),
                                    "descripcion": descripcion.strip(),
                                    "tipo": tipo,
                                    "categoria": prod.get("categoria"),  # Keep existing categoria
                                    "precio_unitario": str(int(precio)),
                                    "costo": str(int(costo)),
                                    "moneda": moneda,
                                    "impuesto_porcentaje": str(float(impuesto)),
                                    "imagen_url": imagen_url.strip() if imagen_url else "",
                                    "activo": bool(activo),
                                }
                                if cuenta_contable_value:
                                    payload["cuenta_contable"] = cuenta_contable_value
                                
                                try:
                                    result, err = api.update_producto(prod["id"], payload)
                                    if err:
                                        notify_error(f"No se pudo guardar el producto", {"error": str(err), "payload": payload})
                                    else:
                                        notify_success(f"Producto **{nombre}** actualizado correctamente")
                                        # Clear ALL caches to refresh data everywhere
                                        st.cache_data.clear()
                                        st.cache_resource.clear()
                                        import time
                                        time.sleep(0.5)
                                        st.rerun()
                                except Exception as e:
                                    notify_error(f"Error procesando los datos", {"error": str(e), "type": type(e).__name__})

    # ── Categories ────────────────────────────────────────────────────────────
    with tab_cats:
        cats_data, cats_err = api.list_categorias()
        if cats_err:
            notify_error("No se pudieron cargar las categorías", {"details": str(cats_err)})
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
                    notify_error("El nombre de la categoría es obligatorio")
                else:
                    result, err = api.create_categoria({"nombre": cat_nombre, "descripcion": cat_desc})
                    if err:
                        notify_error("No se pudo crear la categoría", {"details": str(err)})
                    else:
                        notify_success(f"Categoría **{cat_nombre}** creada correctamente")
                        st.rerun()
