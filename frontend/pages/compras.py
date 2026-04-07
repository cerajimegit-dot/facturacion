"""Compras (Purchases) page."""
import streamlit as st
import pandas as pd
import datetime
import api_client as api
from helpers import results, fmt, notify_success, notify_error, notify_info, show_session_notifications


def render():
    show_session_notifications()
    st.header("🛒 Compras")

    tab_compras, tab_proveedores, tab_gastos = st.tabs(["📦 Compras", "🏪 Proveedores", "💸 Gastos"])

    # ── COMPRAS ───────────────────────────────────────────────────────────────
    with tab_compras:
        st.subheader("Registro de Compras")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            estado_filter = st.selectbox(
                "Filtrar por Estado",
                ["todos", "pendiente", "recepcionada", "cancelada"],
                key="compra_estado"
            )
        with col2:
            search = st.text_input("🔍 Buscar por número o proveedor", placeholder="FAC-001...", key="compra_search")
        with col3:
            if st.button("🔄 Actualizar", use_container_width=True):
                st.rerun()

        # List compras
        estado_param = None if estado_filter == "todos" else estado_filter
        data, err = api.list_compras(estado=estado_param, search=search)
        
        if err:
            notify_error("No se pudieron cargar las compras", {"details": str(err)})
        else:
            compras = results(data)
            
            if not compras:
                st.info("📭 No hay compras registradas. ¡Crea una nueva!")
                
                if st.button("➕ Nueva Compra", type="primary", use_container_width=True):
                    st.session_state.show_new_compra = True
            else:
                # Resumen KPIs
                col1, col2, col3, col4 = st.columns(4)
                total_compras = sum(float(c.get("total", 0)) for c in compras)
                compras_pendientes = len([c for c in compras if c.get("estado") == "pendiente"])
                compras_recibidas = len([c for c in compras if c.get("estado") == "recepcionada"])
                
                with col1:
                    st.metric("Total Compras", fmt(total_compras, "₲"))
                with col2:
                    st.metric("Pendientes", f"{compras_pendientes} 🔴")
                with col3:
                    st.metric("Recibidas", f"{compras_recibidas} ✅")
                with col4:
                    st.metric("Total", f"{len(compras)}")

                # Tabla de compras
                df = pd.DataFrame(compras)
                display_cols = [c for c in ["numero", "proveedor_nombre", "fecha", "estado", "total", "moneda"] 
                               if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)

                # Expandibles para detalles
                for compra in compras:
                    estado_badge = "🔴" if compra.get("estado") == "pendiente" else "✅" if compra.get("estado") == "recepcionada" else "❌"
                    with st.expander(f"{estado_badge} **{compra.get('numero', '')}** — {compra.get('proveedor_nombre', '')} | {fmt(compra.get('total', 0), '₲')}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.write(f"**Proveedor:** {compra.get('proveedor_nombre', '-')}")
                            st.write(f"**País:** {compra.get('pais', '-')}")
                            st.write(f"**Fecha:** {compra.get('fecha', '-')}")
                        with col2:
                            st.write(f"**Estado:** {compra.get('estado', '-').upper()}")
                            st.write(f"**Moneda:** {compra.get('moneda', 'PYG')}")
                            if compra.get("moneda") == "USD" and compra.get("cotizacion_usd"):
                                st.write(f"**Cotización USD:** {fmt(compra.get('cotizacion_usd', 0), 'Gs. ')}/USD")
                        with col3:
                            st.write(f"**Subtotal:** {fmt(compra.get('subtotal', 0), '₲')}")
                            st.write(f"**Impuestos:** {fmt(compra.get('impuestos_total', 0), '₲')}")
                            st.write(f"**Total:** {fmt(compra.get('total', 0), '₲')}")

                        # Acciones según estado
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if compra.get("estado") == "pendiente":
                                if st.button("✅ Recibir", key=f"recibir_{compra['id']}", use_container_width=True):
                                    ok, err = api.recibir_compra(compra["id"])
                                    if ok:
                                        notify_success(f"Compra **{compra.get('numero')}** recibida y productos ingresados al stock.")
                                        st.rerun()
                                    else:
                                        notify_error("No se pudo recibir la compra", {"details": str(err)})

                        with col2:
                            if compra.get("estado") == "pendiente":
                                if st.button("❌ Cancelar", key=f"cancelar_{compra['id']}", use_container_width=True):
                                    ok, err = api.cancelar_compra(compra["id"])
                                    if ok:
                                        notify_success(f"Compra **{compra.get('numero')}** cancelada.")
                                        st.rerun()
                                    else:
                                        notify_error("No se pudo cancelar la compra", {"details": str(err)})

                        with col3:
                            if st.button("🗑️ Eliminar", key=f"del_compra_{compra['id']}", use_container_width=True):
                                ok, err = api.delete_compra(compra["id"])
                                if ok:
                                    notify_success(f"Compra **{compra.get('numero')}** eliminada.")
                                    st.rerun()
                                else:
                                    notify_error("No se pudo eliminar la compra", {"details": str(err)})

        # Nueva Compra
        if st.button("➕ Nueva Compra", type="primary", use_container_width=True, key="new_compra_btn"):
            st.session_state.show_new_compra = True

        if st.session_state.get("show_new_compra"):
            st.divider()
            st.subheader("📝 Nueva Compra")

            # Init items
            if "compra_items" not in st.session_state:
                st.session_state.compra_items = []
            if "compra_numero" not in st.session_state:
                st.session_state.compra_numero = ""
            if "compra_proveedor" not in st.session_state:
                st.session_state.compra_proveedor = ""
            if "compra_almacen" not in st.session_state:
                st.session_state.compra_almacen = ""
            if "compra_fecha" not in st.session_state:
                st.session_state.compra_fecha = datetime.date.today()
            if "compra_moneda" not in st.session_state:
                st.session_state.compra_moneda = "PYG"
            if "compra_cotizacion" not in st.session_state:
                st.session_state.compra_cotizacion = 0.0

            # Información de la compra
            col1, col2 = st.columns(2)

            # Proveedores
            prov_data, err = api.list_proveedores() if not err else ([], None)
            proveedores = results(prov_data) if prov_data else []
            proveedor_options = {f"{p.get('nombre', '')} ({p.get('pais', '')}": p for p in proveedores}

            with col1:
                st.session_state.compra_numero = st.text_input("Número de Factura *", placeholder="FAC-2024-001", value=st.session_state.compra_numero)
                st.session_state.compra_proveedor = st.selectbox("Proveedor *", list(proveedor_options.keys()) if proveedor_options else [], index=0)
                st.session_state.compra_fecha = st.date_input("Fecha *", value=st.session_state.compra_fecha)

            with col2:
                almacenes_data, _ = api.list_almacenes()
                almacenes = results(almacenes_data) if almacenes_data else []
                almacen_options = {f"{a.get('codigo', '')} - {a.get('nombre', '')}": a for a in almacenes}
                st.session_state.compra_almacen = st.selectbox("Almacén Destino *", list(almacen_options.keys()) if almacen_options else [], index=0)
                
                st.session_state.compra_moneda = st.selectbox("Moneda", ["PYG", "USD"], index=0 if st.session_state.compra_moneda == "PYG" else 1)
                if st.session_state.compra_moneda == "USD":
                    st.session_state.compra_cotizacion = st.number_input("Cotización USD/PYG *", min_value=0.0, value=st.session_state.compra_cotizacion, step=100.0)

            st.write("**Ítems de la Compra** (Productos o Servicios)")
            
            # Init session state para item actual
            if "item_desc_temp" not in st.session_state:
                st.session_state.item_desc_temp = ""
            if "item_cant_temp" not in st.session_state:
                st.session_state.item_cant_temp = 1.0
            if "item_precio_temp" not in st.session_state:
                st.session_state.item_precio_temp = 0.0
            if "item_iva_temp" not in st.session_state:
                st.session_state.item_iva_temp = 10.0
            if "show_new_producto" not in st.session_state:
                st.session_state.show_new_producto = False
            if "item_producto_id" not in st.session_state:
                st.session_state.item_producto_id = None
            
            # Fila 1: Búsqueda de Producto/Servicio
            st.write("📦 **Seleccionar Producto o Servicio**")
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                # Búsqueda de productos
                search_term = st.text_input(
                    "🔍 Buscar producto/servicio",
                    placeholder="Ingresa nombre o SKU...",
                    key="producto_search"
                )
                
                if search_term:
                    # Buscar productos
                    prod_data, err = api.list_productos(search=search_term)
                    productos = results(prod_data) if prod_data else []
                    
                    if productos:
                        # Crear opciones
                        opciones = {
                            f"[{p.get('sku', 'SIN SKU')}] {p.get('nombre', '')}" : p
                            for p in productos
                        }
                        
                        opcion_seleccionada = st.selectbox(
                            "Resultados encontrados:",
                            list(opciones.keys()),
                            key="producto_select"
                        )
                        
                        if opcion_seleccionada:
                            producto = opciones[opcion_seleccionada]
                            st.session_state.item_producto_id = producto.get('id')
                            st.session_state.item_desc_temp = producto.get('nombre', '')
                            st.session_state.item_precio_temp = float(producto.get('precio_unitario', 0))
                            st.session_state.item_iva_temp = float(producto.get('impuesto_porcentaje', 10))
                            
                            # Mostrar resumen del producto
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.caption(f"SKU: {producto.get('sku')}")
                            with col_b:
                                st.caption(f"Tipo: {producto.get('tipo', 'producto')}")
                            with col_c:
                                st.caption(f"Precio: {fmt(float(producto.get('precio_unitario', 0)), '₲')}")
                    else:
                        st.warning(f"❌ No se encontraron productos con '{search_term}'")
                        if st.button("➕ Crear nuevo producto", key="btn_crear_prod_from_search"):
                            st.session_state.show_new_producto = True
                            st.session_state.item_desc_temp = search_term
            
            with col2:
                if st.button("➕ Crear Nuevo", key="btn_crear_producto"):
                    st.session_state.show_new_producto = True
            
            # Dialog para crear nuevo producto
            if st.session_state.show_new_producto:
                st.divider()
                st.write("**➕ Crear Nuevo Producto/Servicio**")
                
                col1, col2 = st.columns(2)
                with col1:
                    tipo_nuevo = st.radio("Tipo:", ["producto", "servicio"], key="nuevo_prod_tipo")
                with col2:
                    sku_nuevo = st.text_input("SKU *", placeholder="Código único", key="nuevo_prod_sku")
                
                nombre_nuevo = st.text_input("Nombre *", placeholder="Nombre del producto/servicio", value=st.session_state.item_desc_temp, key="nuevo_prod_nombre")
                
                col1, col2 = st.columns(2)
                with col1:
                    precio_nuevo = st.number_input("Precio Unitario *", min_value=0.0, step=1000.0, key="nuevo_prod_precio")
                with col2:
                    iva_nuevo = st.number_input("IVA %", min_value=0.0, max_value=100.0, value=10.0, step=0.5, key="nuevo_prod_iva")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("✅ Guardar Producto", key="btn_guardar_prod", use_container_width=True):
                        if not sku_nuevo or not nombre_nuevo or precio_nuevo < 0:
                            notify_error("❌ Completa SKU, Nombre y Precio")
                        else:
                            payload = {
                                "sku": sku_nuevo,
                                "nombre": nombre_nuevo,
                                "tipo": tipo_nuevo,
                                "precio_unitario": precio_nuevo,
                                "impuesto_porcentaje": iva_nuevo
                            }
                            result, err = api.create_producto(payload)
                            if err:
                                notify_error(f"❌ Error al crear producto: {err}")
                            else:
                                st.session_state.item_producto_id = result.get('id')
                                st.session_state.item_desc_temp = result.get('nombre')
                                st.session_state.item_precio_temp = float(result.get('precio_unitario', 0))
                                st.session_state.item_iva_temp = float(result.get('impuesto_porcentaje', 10))
                                st.session_state.show_new_producto = False
                                notify_success(f"✅ Producto '{nombre_nuevo}' creado exitosamente")
                                st.rerun()
                
                with col2:
                    if st.button("❌ Cancelar", key="btn_cancelar_prod", use_container_width=True):
                        st.session_state.show_new_producto = False
                        st.rerun()
            
            st.divider()
            
            # Fila 2: Detalles del item - Descripción y Cantidad
            col1, col2 = st.columns([3, 1])
            with col1:
                st.session_state.item_desc_temp = st.text_input(
                    "Descripción del Item *", 
                    placeholder="Nombre del producto/servicio",
                    value=st.session_state.item_desc_temp,
                    key="item_desc_input"
                )
            with col2:
                st.session_state.item_cant_temp = st.number_input(
                    "Cantidad *", 
                    min_value=0.01, 
                    value=st.session_state.item_cant_temp,
                    step=1.0,
                    key="item_cant_input"
                )

            # Fila 3: Precio, IVA y Total Item
            col1, col2, col3 = st.columns([2, 1, 1.5])
            with col1:
                st.session_state.item_precio_temp = st.number_input(
                    "Precio Unitario *", 
                    min_value=0.0, 
                    value=st.session_state.item_precio_temp,
                    step=1000.0,
                    key="item_precio_input"
                )
            with col2:
                st.session_state.item_iva_temp = st.number_input(
                    "IVA %", 
                    min_value=0.0, 
                    max_value=100.0, 
                    value=st.session_state.item_iva_temp,
                    step=0.5,
                    key="item_iva_input"
                )
            with col3:
                total_item = float(st.session_state.item_cant_temp) * float(st.session_state.item_precio_temp) * (1 + float(st.session_state.item_iva_temp) / 100)
                st.metric("Total Item", fmt(total_item, "₲"))

            # Botón agregar
            if st.button("➕ Agregar Item", use_container_width=True, key="btn_agregar_item"):
                if st.session_state.item_desc_temp and st.session_state.item_cant_temp > 0 and st.session_state.item_precio_temp > 0:
                    st.session_state.compra_items.append({
                        "descripcion": st.session_state.item_desc_temp,
                        "cantidad": st.session_state.item_cant_temp,
                        "precio_unitario": st.session_state.item_precio_temp,
                        "impuesto_porcentaje": st.session_state.item_iva_temp,
                        "producto_id": st.session_state.item_producto_id
                    })
                    # Limpiar campos después de agregar
                    st.session_state.item_desc_temp = ""
                    st.session_state.item_cant_temp = 1.0
                    st.session_state.item_precio_temp = 0.0
                    st.session_state.item_iva_temp = 10.0
                    st.session_state.item_producto_id = None
                    notify_success(f"✅ Item agregado exitosamente")
                    st.rerun()
                else:
                    notify_error("❌ Completa: descripción, cantidad y precio deben ser mayores a 0")

            # Items agregados
            if st.session_state.compra_items:
                st.write("**Items Agregados:**")
                
                # Tabla de items
                col1, col2, col3, col4, col5 = st.columns([2, 1, 1.5, 1, 0.5])
                with col1:
                    st.write("**Descripción**")
                with col2:
                    st.write("**Cant.**")
                with col3:
                    st.write("**Precio Unit.**")
                with col4:
                    st.write("**Total**")
                with col5:
                    st.write("**Acción**")
                
                # Items
                for idx, item in enumerate(st.session_state.compra_items):
                    col1, col2, col3, col4, col5 = st.columns([2, 1, 1.5, 1, 0.5])
                    
                    qty = float(item.get('cantidad', 0))
                    price = float(item.get('precio_unitario', 0))
                    iva_pct = float(item.get('impuesto_porcentaje', 0))
                    
                    subtotal_item = qty * price
                    iva_item = subtotal_item * (iva_pct / 100)
                    total_item = subtotal_item + iva_item
                    
                    with col1:
                        st.write(item.get('descripcion'))
                    with col2:
                        st.write(f"{qty:.0f}")
                    with col3:
                        st.write(fmt(price, "₲"))
                    with col4:
                        st.write(fmt(total_item, "₲"))
                    with col5:
                        if st.button("❌", key=f"del_item_{idx}", use_container_width=True):
                            st.session_state.compra_items.pop(idx)
                            st.rerun()
                
                st.divider()
                
                # Resumen totales
                subtotal_compra = sum(
                    float(item.get('cantidad', 0)) * float(item.get('precio_unitario', 0))
                    for item in st.session_state.compra_items
                )
                impuestos_compra = sum(
                    float(item.get('cantidad', 0)) * float(item.get('precio_unitario', 0)) * (float(item.get('impuesto_porcentaje', 0)) / 100)
                    for item in st.session_state.compra_items
                )
                total_compra = subtotal_compra + impuestos_compra
                
                col1, col2, col3 = st.columns([2, 1, 1.5])
                with col1:
                    st.write("")
                with col2:
                    st.write("**Subtotal:**")
                with col3:
                    st.metric("", fmt(subtotal_compra, "₲"), label_visibility="collapsed")
                
                col1, col2, col3 = st.columns([2, 1, 1.5])
                with col1:
                    st.write("")
                with col2:
                    st.write("**Impuestos IVA:**")
                with col3:
                    st.metric("", fmt(impuestos_compra, "₲"), label_visibility="collapsed")
                
                col1, col2, col3 = st.columns([2, 1, 1.5])
                with col1:
                    st.write("")
                with col2:
                    st.write("**🛒 TOTAL COMPRA:**")
                with col3:
                    st.metric("", fmt(total_compra, "₲"), label_visibility="collapsed")

            # Botón guardar
            if st.button("💾 Guardar Compra", type="primary", use_container_width=True, key="btn_guardar_compra"):
                if not st.session_state.compra_numero or not st.session_state.compra_proveedor or not st.session_state.compra_almacen or not st.session_state.compra_items:
                    notify_error("Completa todos los campos y agrega al menos un item.")
                else:
                    # Re-obtener opciones para validar
                    prov_data_check, _ = api.list_proveedores()
                    proveedores_check = results(prov_data_check) if prov_data_check else []
                    proveedor_options_check = {f"{p.get('nombre', '')} ({p.get('pais', '')}": p for p in proveedores_check}
                    
                    almacenes_data_check, _ = api.list_almacenes()
                    almacenes_check = results(almacenes_data_check) if almacenes_data_check else []
                    almacen_options_check = {f"{a.get('codigo', '')} - {a.get('nombre', '')}": a for a in almacenes_check}
                    
                    if st.session_state.compra_proveedor not in proveedor_options_check:
                        notify_error("Proveedor inválido. Recarga la página.")
                    elif st.session_state.compra_almacen not in almacen_options_check:
                        notify_error("Almacén inválido. Recarga la página.")
                    else:
                        proveedor = proveedor_options_check[st.session_state.compra_proveedor]
                        almacen = almacen_options_check[st.session_state.compra_almacen]

                        payload = {
                            "numero": st.session_state.compra_numero,
                            "fecha": st.session_state.compra_fecha.isoformat(),
                            "proveedor": proveedor["id"],
                            "almacen": almacen["id"],
                            "moneda": st.session_state.compra_moneda,
                            "estado": "pendiente",
                            "detalles": st.session_state.compra_items
                        }

                        if st.session_state.compra_moneda == "USD":
                            payload["cotizacion_usd"] = str(st.session_state.compra_cotizacion)

                        result, err = api.create_compra(payload)
                        if err:
                            # Mostrar errores detallados
                            error_msg = str(err)
                            if 'detalles' in error_msg.lower():
                                notify_error("❌ Error en los items: Verifica que cada item tenga descripción, cantidad y precio válidos.")
                            elif 'cotizacion' in error_msg.lower():
                                notify_error("❌ Error: La cotización USD es obligatoria")
                            else:
                                notify_error(f"❌ No se pudo crear la compra: {error_msg}")
                            st.warning(f"📋 Detalles técnicos: {error_msg}")
                        else:
                            # Verificar que la compra se creó correctamente
                            compra_id = result.get('id')
                            if not compra_id:
                                notify_error("❌ La compra se creó pero sin ID. Por favor recarga la página.")
                            elif result.get('total') == 0:
                                notify_error("❌ ⚠️ ALERTA: La compra se creó pero sin detalles. Total = 0. Por favor revisa.")
                            else:
                                # Todo bien
                                total_items = len(st.session_state.compra_items)
                                total_cantidad = sum(float(item.get('cantidad', 0)) for item in st.session_state.compra_items)
                                
                                notify_success(f"""
✅ **Compra registrada correctamente**
- Número: {st.session_state.compra_numero}
- Items: {total_items}
- Cantidad total: {total_cantidad} unidades
- Total: {fmt(result.get('total', 0), '₲')}
- Estado: {result.get('estado')}
                                """)
                                
                                st.session_state.compra_items = []
                                st.session_state.show_new_compra = False
                                st.session_state.compra_numero = ""
                                st.session_state.compra_proveedor = ""
                                st.session_state.compra_almacen = ""
                                st.rerun()

    # ── PROVEEDORES ───────────────────────────────────────────────────────────
    with tab_proveedores:
        st.subheader("Gestión de Proveedores")

        col1, col2 = st.columns(2)
        with col1:
            search = st.text_input("🔍 Buscar proveedor", placeholder="Nombre, RUC, país...", key="prov_search")
        with col2:
            if st.button("🔄 Actualizar", use_container_width=True, key="refresh_prov"):
                st.rerun()

        data, err = api.list_proveedores(search=search)
        if err:
            notify_error("No se pudieron cargar los proveedores", {"details": str(err)})
        else:
            proveedores = results(data)

            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Proveedores", len(proveedores))
            with col2:
                activos = len([p for p in proveedores if p.get("activo")])
                st.metric("Activos", activos)

            if not proveedores:
                st.info("📭 No hay proveedores registrados.")
            else:
                df = pd.DataFrame(proveedores)
                display_cols = [c for c in ["nombre", "ruc_numero", "pais", "email", "telefono", "activo"] 
                               if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)

                # Expandibles
                for prov in proveedores:
                    with st.expander(f"**{prov.get('nombre', '')}** ({prov.get('pais', '')}) — RUC: {prov.get('ruc_numero', '')}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Email:** {prov.get('email', '-')}")
                            st.write(f"**Teléfono:** {prov.get('telefono', '-')}")
                            st.write(f"**Contacto:** {prov.get('contacto_nombre', '-')}")
                        with col2:
                            st.write(f"**Importancia:** {prov.get('importancia', '-').upper()}")
                            st.write(f"**Días Crédito:** {prov.get('dias_credito', 0)} días")
                            st.write(f"**Total Compras:** {prov.get('total_compras', 0)}")

                        if st.button("🗑️ Eliminar", key=f"del_prov_{prov['id']}"):
                            ok, err = api.delete_proveedor(prov["id"])
                            if ok:
                                notify_success(f"Proveedor **{prov.get('nombre')}** eliminado.")
                                st.rerun()
                            else:
                                notify_error("Error al eliminar proveedor", {"details": str(err)})

        if st.button("➕ Nuevo Proveedor", type="primary", use_container_width=True, key="new_prov_btn"):
            st.session_state.show_new_prov = True

        if st.session_state.get("show_new_prov"):
            st.divider()
            st.subheader("📝 Nuevo Proveedor")

            with st.form("new_proveedor"):
                col1, col2 = st.columns(2)

                with col1:
                    nombre = st.text_input("Nombre *", placeholder="Nombre de la empresa")
                    ruc = st.text_input("RUC *", placeholder="80123456-7")
                    pais = st.text_input("País *", placeholder="Paraguay")

                with col2:
                    email = st.text_input("Email", placeholder="contacto@empresa.com")
                    telefono = st.text_input("Teléfono", placeholder="+595 981 234567")
                    contacto = st.text_input("Contacto", placeholder="Nombre de contacto")

                direccion = st.text_area("Dirección", placeholder="Calle, número, ciudad")

                col1, col2 = st.columns(2)
                with col1:
                    importancia = st.selectbox("Importancia", ["bajo", "medio", "alto"])
                with col2:
                    dias_credito = st.number_input("Días de Crédito", min_value=0, value=0, step=1)

                if st.form_submit_button("💾 Guardar Proveedor", type="primary", use_container_width=True):
                    if not nombre or not ruc or not pais:
                        notify_error("Nombre, RUC y País son obligatorios.")
                    else:
                        payload = {
                            "nombre": nombre,
                            "ruc_numero": ruc,
                            "pais": pais,
                            "email": email,
                            "telefono": telefono,
                            "contacto_nombre": contacto,
                            "direccion": direccion,
                            "importancia": importancia,
                            "dias_credito": dias_credito
                        }

                        result, err = api.create_proveedor(payload)
                        if err:
                            notify_error("No se pudo crear el proveedor", {"details": str(err)})
                        else:
                            notify_success(f"✅ Proveedor **{nombre}** creado correctamente.")
                            st.session_state.show_new_prov = False
                            st.rerun()

    # ── GASTOS ────────────────────────────────────────────────────────────────
    with tab_gastos:
        st.subheader("Gestión de Gastos")

        col1, col2, col3 = st.columns(3)
        with col1:
            # Categorías
            cat_data, _ = api.list_categorias_gasto()
            categorias = results(cat_data) if cat_data else []
            categoria_names = [c.get("nombre") for c in categorias]
            
            cat_filter = st.selectbox("Filtrar por Categoría", ["todas"] + categoria_names, key="gasto_cat")
        with col2:
            aprobado_filter = st.selectbox("Estado", ["todos", "aprobados", "pendientes"], key="gasto_aprobado")
        with col3:
            if st.button("🔄 Actualizar", use_container_width=True, key="refresh_gastos"):
                st.rerun()

        data, err = api.list_gastos()
        if err:
            notify_error("No se pudieron cargar los gastos", {"details": str(err)})
        else:
            gastos = results(data) if data else []

            # Filtrar
            if cat_filter != "todas":
                gastos = [g for g in gastos if g.get("categoria_nombre") == cat_filter]
            if aprobado_filter == "aprobados":
                gastos = [g for g in gastos if g.get("aprobado")]
            elif aprobado_filter == "pendientes":
                gastos = [g for g in gastos if not g.get("aprobado")]

            # Métricas
            col1, col2, col3, col4 = st.columns(4)
            total_gastos = sum(float(g.get("monto", 0)) for g in gastos)
            aprobados = len([g for g in gastos if g.get("aprobado")])
            pendientes = len([g for g in gastos if not g.get("aprobado")])

            with col1:
                st.metric("Total Gastos", fmt(total_gastos, "₲"))
            with col2:
                st.metric("Aprobados", f"{aprobados} ✅")
            with col3:
                st.metric("Pendientes", f"{pendientes} 🔴")
            with col4:
                st.metric("Total Registros", len(gastos))

            if not gastos:
                st.info("📭 No hay gastos registrados.")
            else:
                df = pd.DataFrame(gastos)
                display_cols = [c for c in ["fecha", "categoria_nombre", "descripcion", "monto", "moneda", "aprobado"] 
                               if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)

                # Expandibles
                for gasto in gastos:
                    estado_badge = "✅" if gasto.get("aprobado") else "🔴"
                    with st.expander(f"{estado_badge} **{gasto.get('categoria_nombre', '')}** | {fmt(gasto.get('monto', 0), '₲')} | {gasto.get('fecha', '')}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Descripción:** {gasto.get('descripcion', '-')}")
                            st.write(f"**Categoría:** {gasto.get('categoria_nombre', '-')}")
                            st.write(f"**Fecha:** {gasto.get('fecha', '-')}")
                        with col2:
                            st.write(f"**Monto:** {fmt(gasto.get('monto', 0), '₲')} {gasto.get('moneda', 'PYG')}")
                            st.write(f"**Comprobante:** {gasto.get('comprobante', '-') or 'N/A'}")
                            st.write(f"**Estado:** {'Aprobado ✅' if gasto.get('aprobado') else 'Pendiente 🔴'}")

                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if not gasto.get("aprobado"):
                                if st.button("✅ Aprobar", key=f"aprobar_{gasto['id']}", use_container_width=True):
                                    ok, err = api.aprobar_gasto(gasto["id"])
                                    if ok:
                                        notify_success("Gasto aprobado.")
                                        st.rerun()
                                    else:
                                        notify_error("Error al aprobar", {"details": str(err)})
                        with col2:
                            pass
                        with col3:
                            if st.button("🗑️ Eliminar", key=f"del_gasto_{gasto['id']}", use_container_width=True):
                                ok, err = api.delete_gasto(gasto["id"])
                                if ok:
                                    notify_success("Gasto eliminado.")
                                    st.rerun()
                                else:
                                    notify_error("Error al eliminar", {"details": str(err)})

        if st.button("➕ Nuevo Gasto", type="primary", use_container_width=True, key="new_gasto_btn"):
            st.session_state.show_new_gasto = True

        if st.session_state.get("show_new_gasto"):
            st.divider()
            st.subheader("📝 Nuevo Gasto")

            with st.form("new_gasto"):
                col1, col2 = st.columns(2)

                # Categorías
                cat_data, _ = api.list_categorias_gasto()
                categorias = results(cat_data) if cat_data else []
                cat_names = {c.get("nombre"): c for c in categorias}

                with col1:
                    fecha = st.date_input("Fecha *", value=datetime.date.today())
                    categoria_name = st.selectbox("Categoría *", list(cat_names.keys()) if cat_names else [])
                    monto = st.number_input("Monto *", min_value=0.0, value=0.0, step=1000.0)

                with col2:
                    moneda = st.selectbox("Moneda", ["PYG", "USD"])
                    comprobante = st.text_input("Comprobante", placeholder="Nro. recibo/factura")
                    descripcion = st.text_area("Descripción", placeholder="Detalles del gasto")

                if st.form_submit_button("💾 Guardar Gasto", type="primary", use_container_width=True):
                    if not categoria_name or monto <= 0:
                        notify_error("Categoría y Monto son obligatorios.")
                    else:
                        categoria = cat_names[categoria_name]

                        payload = {
                            "fecha": fecha.isoformat(),
                            "categoria": categoria["id"],
                            "monto": str(monto),
                            "moneda": moneda,
                            "comprobante": comprobante,
                            "descripcion": descripcion
                        }

                        result, err = api.create_gasto(payload)
                        if err:
                            notify_error("No se pudo crear el gasto", {"details": str(err)})
                        else:
                            notify_success("✅ Gasto registrado correctamente.")
                            st.session_state.show_new_gasto = False
                            st.rerun()


if __name__ == "__main__":
    render()
