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
                display_cols = [c for c in ["numero", "proveedor_nombre", "fecha", "estado", "subtotal", "impuestos_total", "total", "moneda"] 
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
            prov_data, prov_err = api.list_proveedores()
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
                    # Auto-fetch cotización del día
                    cot_data, cot_err = api.get_cotizacion_del_dia(
                        fecha=st.session_state.compra_fecha.isoformat()
                    )
                    if cot_err or not cot_data:
                        st.session_state.compra_cotizacion = 0.0
                        st.error("⚠️ No hay cotización USD/PYG cargada para esta fecha. Cargue la cotización en Contabilidad → Cotizaciones antes de registrar la compra.")
                        st.session_state._compra_sin_cotizacion = True
                    else:
                        tasa = float(cot_data.get("tasa", 0))
                        st.session_state.compra_cotizacion = tasa
                        st.session_state._compra_sin_cotizacion = False
                        st.success(f"💱 Cotización del día: 1 USD = {tasa:,.0f} PYG")
                else:
                    st.session_state._compra_sin_cotizacion = False

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
                            st.session_state.item_cuenta_desc_temp = producto.get('cuenta_contable_desc', '')
                            
                            # Mostrar resumen del producto
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                st.caption(f"SKU: {producto.get('sku')}")
                            with col_b:
                                st.caption(f"Tipo: {producto.get('tipo', 'producto')}")
                            with col_c:
                                st.caption(f"Precio: {fmt(float(producto.get('precio_unitario', 0)), '₲')}")
                            
                            # Mostrar cuenta contable del producto
                            cuenta_desc = producto.get('cuenta_contable_desc')
                            if cuenta_desc:
                                st.caption(f"📒 Cuenta contable: {cuenta_desc}")
                            else:
                                st.warning("⚠️ Este producto no tiene cuenta contable asignada. Asígnala en Productos para que el asiento contable se genere correctamente.")
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
                # Precio incluye IVA
                total_item = float(st.session_state.item_cant_temp) * float(st.session_state.item_precio_temp)
                st.metric("Total Item", fmt(total_item, "₲"))

            # Botón agregar
            if st.button("➕ Agregar Item", use_container_width=True, key="btn_agregar_item"):
                if st.session_state.item_desc_temp and st.session_state.item_cant_temp > 0 and st.session_state.item_precio_temp > 0:
                    st.session_state.compra_items.append({
                        "descripcion": st.session_state.item_desc_temp,
                        "cantidad": st.session_state.item_cant_temp,
                        "precio_unitario": st.session_state.item_precio_temp,
                        "impuesto_porcentaje": st.session_state.item_iva_temp,
                        "producto_id": st.session_state.item_producto_id,
                        "cuenta_contable_desc": st.session_state.get("item_cuenta_desc_temp", ""),
                    })
                    # Limpiar campos después de agregar
                    st.session_state.item_desc_temp = ""
                    st.session_state.item_cant_temp = 1.0
                    st.session_state.item_precio_temp = 0.0
                    st.session_state.item_iva_temp = 10.0
                    st.session_state.item_producto_id = None
                    st.session_state.item_cuenta_desc_temp = ""
                    notify_success(f"✅ Item agregado exitosamente")
                    st.rerun()
                else:
                    notify_error("❌ Completa: descripción, cantidad y precio deben ser mayores a 0")

            # Items agregados
            if st.session_state.compra_items:
                st.write("**Items Agregados:**")
                
                # Tabla de items
                col1, col2, col3, col4, col5, col6 = st.columns([2, 0.7, 1.2, 1, 1, 0.5])
                with col1:
                    st.write("**Descripción**")
                with col2:
                    st.write("**Cant.**")
                with col3:
                    st.write("**P.Unit (c/IVA)**")
                with col4:
                    st.write("**Neto**")
                with col5:
                    st.write("**IVA**")
                with col6:
                    st.write("**Acción**")
                
                # Items
                for idx, item in enumerate(st.session_state.compra_items):
                    col1, col2, col3, col4, col5, col6 = st.columns([2, 0.7, 1.2, 1, 1, 0.5])
                    
                    qty = float(item.get('cantidad', 0))
                    price = float(item.get('precio_unitario', 0))
                    iva_pct = float(item.get('impuesto_porcentaje', 0))
                    
                    # Precio incluye IVA
                    total_item = qty * price
                    if iva_pct > 0:
                        neto_item = total_item / (1 + iva_pct / 100)
                        iva_item = total_item - neto_item
                    else:
                        neto_item = total_item
                        iva_item = 0
                    
                    with col1:
                        desc = item.get('descripcion', '')
                        cuenta = item.get('cuenta_contable_desc', '')
                        st.write(desc)
                        if cuenta:
                            st.caption(f"📒 {cuenta}")
                    with col2:
                        st.write(f"{qty:.0f}")
                    with col3:
                        st.write(fmt(price, "₲"))
                    with col4:
                        st.write(fmt(neto_item, "₲"))
                    with col5:
                        st.write(f"{fmt(iva_item, '₲')} ({iva_pct:.0f}%)")
                    with col6:
                        if st.button("❌", key=f"del_item_{idx}", use_container_width=True):
                            st.session_state.compra_items.pop(idx)
                            st.rerun()
                
                st.divider()
                
                # Resumen totales (precio incluye IVA)
                total_compra = sum(
                    float(item.get('cantidad', 0)) * float(item.get('precio_unitario', 0))
                    for item in st.session_state.compra_items
                )
                impuestos_compra = sum(
                    (lambda t, p: t - t / (1 + p / 100) if p > 0 else 0)(
                        float(item.get('cantidad', 0)) * float(item.get('precio_unitario', 0)),
                        float(item.get('impuesto_porcentaje', 0))
                    )
                    for item in st.session_state.compra_items
                )
                subtotal_compra = total_compra - impuestos_compra
                
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

                # ── Vista Previa del Asiento Contable ──────────────────────
                st.divider()
                st.subheader("📋 Vista Previa del Asiento Contable")

                # Obtener datos del proveedor seleccionado
                prov_selected = proveedor_options.get(st.session_state.compra_proveedor, {})
                prov_cuenta_desc = prov_selected.get('cuenta_contable_desc', 'Sin cuenta contable')
                prov_nombre = prov_selected.get('nombre', '')

                # Cotización para conversión USD → PYG
                es_usd = st.session_state.compra_moneda == "USD"
                tasa_cambio = float(st.session_state.compra_cotizacion) if es_usd else 1.0

                if es_usd and tasa_cambio > 0:
                    st.info(f"💱 Asiento en Guaraníes (cotización: 1 USD = {tasa_cambio:,.0f} PYG)")
                elif es_usd:
                    st.warning("⚠️ Sin cotización — los montos se muestran en USD sin convertir")
                    tasa_cambio = 1.0

                def _solo_desc(cuenta):
                    """Devuelve solo la descripción sin el código contable."""
                    if cuenta and " - " in cuenta:
                        return cuenta.split(" - ", 1)[1]
                    return cuenta

                lineas_asiento = []

                for item in st.session_state.compra_items:
                    qty = float(item.get('cantidad', 0))
                    price = float(item.get('precio_unitario', 0))
                    iva_pct = float(item.get('impuesto_porcentaje', 0))

                    # Precio incluye IVA
                    total_linea = qty * price
                    if iva_pct > 0:
                        subtotal_item = total_linea / (1 + iva_pct / 100)
                        iva_item = total_linea - subtotal_item
                    else:
                        subtotal_item = total_linea
                        iva_item = 0

                    # Convertir a PYG
                    subtotal_item *= tasa_cambio
                    iva_item *= tasa_cambio

                    cuenta_prod = _solo_desc(item.get('cuenta_contable_desc', '')) or 'Sin cuenta contable'

                    # Línea DEBE: cuenta del producto (neto sin IVA)
                    lineas_asiento.append({
                        "Cuenta": cuenta_prod,
                        "Descripción": f"Compra {item.get('descripcion', '')}",
                        "Debe": subtotal_item,
                        "Haber": 0,
                    })

                    # Línea DEBE: IVA Crédito Fiscal
                    if iva_item > 0:
                        lineas_asiento.append({
                            "Cuenta": "IVA CRÉDITO FISCAL",
                            "Descripción": f"IVA {iva_pct:.0f}% - {item.get('descripcion', '')}",
                            "Debe": iva_item,
                            "Haber": 0,
                        })

                total_compra_pyg = total_compra * tasa_cambio

                # Línea HABER: cuenta del proveedor (total con IVA)
                lineas_asiento.append({
                    "Cuenta": _solo_desc(prov_cuenta_desc) or 'Sin cuenta contable',
                    "Descripción": f"Proveedor: {prov_nombre}",
                    "Debe": 0,
                    "Haber": total_compra_pyg,
                })

                df_asiento = pd.DataFrame(lineas_asiento)
                df_asiento["Debe"] = df_asiento["Debe"].apply(lambda x: fmt(x, "₲") if x > 0 else "")
                df_asiento["Haber"] = df_asiento["Haber"].apply(lambda x: fmt(x, "₲") if x > 0 else "")

                st.dataframe(df_asiento, use_container_width=True, hide_index=True)

                # Validación de balance
                total_debe_preview = total_compra_pyg

                col_d, col_h = st.columns(2)
                with col_d:
                    st.write(f"**Total Debe:** {fmt(total_debe_preview, '₲')}")
                with col_h:
                    st.write(f"**Total Haber:** {fmt(total_compra_pyg, '₲')}")

                if abs(total_debe_preview - total_compra_pyg) < 0.01:
                    st.success("✅ Asiento balanceado")
                else:
                    st.error("❌ Asiento desbalanceado")

            # Botón guardar
            if st.button("💾 Guardar Compra", type="primary", use_container_width=True, key="btn_guardar_compra"):
                if st.session_state.get("_compra_sin_cotizacion"):
                    notify_error("No se puede registrar: no hay cotización USD/PYG para la fecha seleccionada. Cargue la cotización en Contabilidad → Cotizaciones.")
                else:
                    campos_faltantes = []
                    if not st.session_state.compra_numero:
                        campos_faltantes.append("Número de Factura")
                    if not st.session_state.compra_proveedor:
                        campos_faltantes.append("Proveedor")
                    if not st.session_state.compra_almacen:
                        campos_faltantes.append("Almacén")
                    if not st.session_state.compra_items:
                        campos_faltantes.append("al menos un ítem")
                    if campos_faltantes:
                        notify_error(f"Falta completar: {', '.join(campos_faltantes)}")
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
                display_cols = [c for c in ["nombre", "ruc_numero", "ruc_alfanumerico", "pais", "email", "email_set", "emite_electronica", "timbrado_numero", "activo"] 
                               if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)

                # Expandibles
                for prov in proveedores:
                    with st.expander(f"**{prov.get('nombre', '')}** ({prov.get('pais', '')}) — RUC: {prov.get('ruc_numero', '')}"):
                        st.write("**Información General**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Email:** {prov.get('email', '-')}")
                            st.write(f"**Email SET:** {prov.get('email_set', '-')}")
                            st.write(f"**Teléfono:** {prov.get('telefono', '-')}")
                            st.write(f"**Contacto:** {prov.get('contacto_nombre', '-')}")
                        with col2:
                            st.write(f"**Importancia:** {prov.get('importancia', '-').upper()}")
                            st.write(f"**Días Crédito:** {prov.get('dias_credito', 0)} días")
                            st.write(f"**Total Compras:** {prov.get('total_compras', 0)}")
                        
                        st.divider()
                        st.write("**Información Tributaria**")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**RUC Alfanumérico:** {prov.get('ruc_alfanumerico', '-')}")
                            st.write(f"**Emite Electrónica:** {'✅ Sí' if prov.get('emite_electronica') else '❌ No'}")
                        with col2:
                            st.write(f"**Timbrado Número:** {prov.get('timbrado_numero', '-')}")
                            st.write(f"**Timbrado Vencimiento:** {prov.get('timbrado_vencimiento', '-')}")
                        
                        if prov.get('cuenta_contable') or prov.get('cuenta_contable_desc'):
                            st.divider()
                            st.write("**Información Contable**")
                            st.write(f"**Cuenta Contable:** {prov.get('cuenta_contable_desc', prov.get('cuenta_contable', '-'))}")

                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("✏️ Editar", key=f"btn_edit_prov_{prov['id']}", use_container_width=True):
                                st.session_state[f"edit_prov_{prov['id']}"] = True
                        with col2:
                            if st.button("🗑️ Eliminar", key=f"btn_del_prov_{prov['id']}", use_container_width=True):
                                ok, err = api.delete_proveedor(prov["id"])
                                if ok:
                                    notify_success(f"Proveedor **{prov.get('nombre')}** eliminado.")
                                    st.rerun()
                                else:
                                    notify_error("Error al eliminar proveedor", {"details": str(err)})

        # ── Edit Provider Form ──────────────────────────────────────────────
        for prov in proveedores:
            if st.session_state.get(f"edit_prov_{prov['id']}"):
                st.divider()
                st.subheader(f"✏️ Editar Proveedor: {prov.get('nombre', '')}")
                
                with st.form(f"edit_prov_form_{prov['id']}"):
                    st.write("### Información General")
                    col1, col2 = st.columns(2)

                    with col1:
                        nombre = st.text_input("Nombre *", value=prov.get("nombre", ""), placeholder="Nombre de la empresa")
                        ruc = st.text_input("RUC *", value=prov.get("ruc_numero", ""), placeholder="80123456-7")
                        ruc_alfa = st.text_input("RUC Alfanumérico", value=prov.get("ruc_alfanumerico", ""), placeholder="Ej: XX123456789ABC")
                        pais = st.text_input("País *", value=prov.get("pais", ""), placeholder="Paraguay")

                    with col2:
                        email = st.text_input("Email", value=prov.get("email", ""), placeholder="contacto@empresa.com")
                        email_set = st.text_input("Email SET", value=prov.get("email_set", ""), placeholder="set@empresa.com")
                        telefono = st.text_input("Teléfono", value=prov.get("telefono", ""), placeholder="+595 981 234567")
                        contacto = st.text_input("Contacto", value=prov.get("contacto_nombre", ""), placeholder="Nombre de contacto")

                    direccion = st.text_area("Dirección", value=prov.get("direccion", ""), placeholder="Calle, número, ciudad")

                    st.write("### Información Comercial")
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        importancia = st.selectbox("Importancia", ["bajo", "medio", "alto"], index=["bajo", "medio", "alto"].index(prov.get("importancia", "bajo")))
                    with col2:
                        dias_credito = st.number_input("Días de Crédito", min_value=0, value=prov.get("dias_credito", 0), step=1)
                    with col3:
                        emite_elec = st.checkbox("Emite Electrónica", value=prov.get("emite_electronica", False))
                    with col4:
                        pass

                    st.write("### Información Tributaria")
                    col1, col2 = st.columns(2)
                    with col1:
                        timbrado_num = st.text_input("Número Timbrado", value=prov.get("timbrado_numero", "") or "", placeholder="Ej: 12345678")
                    with col2:
                        timbrado_venc_str = prov.get("timbrado_vencimiento")
                        timbrado_venc_value = None
                        if timbrado_venc_str:
                            try:
                                timbrado_venc_value = datetime.datetime.strptime(timbrado_venc_str, "%Y-%m-%d").date()
                            except:
                                timbrado_venc_value = None
                        timbrado_venc = st.date_input("Vencimiento Timbrado", value=timbrado_venc_value)

                    st.write("### Información Contable")
                    cuentas_data, _ = api.list_plan_cuentas()
                    if isinstance(cuentas_data, list):
                        cuentas = cuentas_data
                    elif isinstance(cuentas_data, dict) and "results" in cuentas_data:
                        cuentas = cuentas_data["results"]
                    else:
                        cuentas = []
                    if cuentas:
                        cuenta_options = {f"{c.get('codigo_cuenta')} - {c.get('descripcion')}": c.get('id') for c in cuentas}
                        current_cuenta_id = prov.get('cuenta_contable', '')
                        # Find the option that matches the current ID
                        current_option = None
                        for opt, cuenta_id in cuenta_options.items():
                            if cuenta_id == current_cuenta_id:
                                current_option = opt
                                break
                        cuenta_index = list(cuenta_options.keys()).index(current_option) if current_option else 0
                        cuenta_contable_id = st.selectbox("Cuenta Contable para Compras", options=list(cuenta_options.keys()) if cuenta_options else ["Sin cuentas disponibles"], index=cuenta_index, key=f"edit_prov_cuenta_{prov['id']}")
                        cuenta_contable_value = cuenta_options.get(cuenta_contable_id) if cuenta_contable_id in cuenta_options else None
                    else:
                        st.warning("No hay cuentas contables disponibles. Crea el plan de cuentas primero.")
                        cuenta_contable_value = prov.get('cuenta_contable')

                    col_submit, col_cancel = st.columns(2)
                    with col_submit:
                        if st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True):
                            if not nombre or not ruc or not pais:
                                notify_error("Nombre, RUC y País son obligatorios.")
                            else:
                                payload = {
                                    "nombre": nombre,
                                    "ruc_numero": ruc,
                                    "ruc_alfanumerico": ruc_alfa,
                                    "pais": pais,
                                    "email": email,
                                    "email_set": email_set,
                                    "telefono": telefono,
                                    "contacto_nombre": contacto,
                                    "direccion": direccion,
                                    "importancia": importancia,
                                    "dias_credito": dias_credito,
                                    "emite_electronica": emite_elec,
                                    "timbrado_numero": timbrado_num,
                                    "timbrado_vencimiento": str(timbrado_venc) if timbrado_venc else None
                                }
                                
                                if cuenta_contable_value:
                                    payload["cuenta_contable"] = cuenta_contable_value

                                result, err = api.update_proveedor(prov["id"], payload)
                                if err:
                                    notify_error("No se pudo actualizar el proveedor", {"details": str(err)})
                                else:
                                    notify_success(f"✅ Proveedor **{nombre}** actualizado correctamente.")
                                    st.session_state[f"edit_prov_{prov['id']}"] = False
                                    st.rerun()
                    with col_cancel:
                        if st.form_submit_button("❌ Cancelar", use_container_width=True):
                            st.session_state[f"edit_prov_{prov['id']}"] = False
                            st.rerun()

        if st.button("➕ Nuevo Proveedor", type="primary", use_container_width=True, key="new_prov_btn"):
            st.session_state.show_new_prov = True

        if st.session_state.get("show_new_prov"):
            st.divider()
            st.subheader("📝 Nuevo Proveedor")

            with st.form("new_proveedor"):
                st.write("### Información General")
                col1, col2 = st.columns(2)

                with col1:
                    nombre = st.text_input("Nombre *", placeholder="Nombre de la empresa")
                    ruc = st.text_input("RUC *", placeholder="80123456-7")
                    ruc_alfa = st.text_input("RUC Alfanumérico", placeholder="Ej: XX123456789ABC")
                    pais = st.text_input("País *", placeholder="Paraguay")

                with col2:
                    email = st.text_input("Email", placeholder="contacto@empresa.com")
                    email_set = st.text_input("Email SET", placeholder="set@empresa.com")
                    telefono = st.text_input("Teléfono", placeholder="+595 981 234567")
                    contacto = st.text_input("Contacto", placeholder="Nombre de contacto")

                direccion = st.text_area("Dirección", placeholder="Calle, número, ciudad")

                st.write("### Información Comercial")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    importancia = st.selectbox("Importancia", ["bajo", "medio", "alto"])
                with col2:
                    dias_credito = st.number_input("Días de Crédito", min_value=0, value=0, step=1)
                with col3:
                    emite_elec = st.checkbox("Emite Electrónica", value=False)
                with col4:
                    pass

                st.write("### Información Tributaria")
                col1, col2 = st.columns(2)
                with col1:
                    timbrado_num = st.text_input("Número Timbrado", placeholder="Ej: 12345678")
                with col2:
                    timbrado_venc = st.date_input("Vencimiento Timbrado", value=None)

                st.write("### Información Contable")
                cuentas_data, _ = api.list_plan_cuentas()
                if isinstance(cuentas_data, list):
                    cuentas = cuentas_data
                elif isinstance(cuentas_data, dict) and "results" in cuentas_data:
                    cuentas = cuentas_data["results"]
                else:
                    cuentas = []
                if cuentas:
                    cuenta_options = {f"{c.get('codigo_cuenta')} - {c.get('descripcion')}": c.get('id') for c in cuentas}
                    cuenta_contable = st.selectbox("Cuenta Contable para Compras", options=list(cuenta_options.keys()) if cuenta_options else ["Sin cuentas disponibles"], key="prov_cuenta_contable")
                    cuenta_contable_value = cuenta_options.get(cuenta_contable) if cuenta_contable in cuenta_options else None
                else:
                    st.warning("No hay cuentas contables disponibles. Crea el plan de cuentas primero.")
                    cuenta_contable_value = None

                if st.form_submit_button("💾 Guardar Proveedor", type="primary", use_container_width=True):
                    if not nombre or not ruc or not pais:
                        notify_error("Nombre, RUC y País son obligatorios.")
                    else:
                        payload = {
                            "nombre": nombre,
                            "ruc_numero": ruc,
                            "ruc_alfanumerico": ruc_alfa,
                            "pais": pais,
                            "email": email,
                            "email_set": email_set,
                            "telefono": telefono,
                            "contacto_nombre": contacto,
                            "direccion": direccion,
                            "importancia": importancia,
                            "dias_credito": dias_credito,
                            "emite_electronica": emite_elec,
                            "timbrado_numero": timbrado_num,
                            "timbrado_vencimiento": str(timbrado_venc) if timbrado_venc else None
                        }
                        
                        if cuenta_contable_value:
                            payload["cuenta_contable"] = cuenta_contable_value

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
