"""Ventas, Cotizaciones and Cuentas por Cobrar page."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results, fmt, notify_success, notify_error, notify_info, show_session_notifications


def render():
    show_session_notifications()
    st.header("🧾 Ventas")

    tab_ventas, tab_nueva, tab_rapida, tab_cxc, tab_nc, tab_cotiz = st.tabs([
        "📋 Ventas", "➕ Nueva Venta", "⚡ Carga Rápida", "💳 Cuentas por Cobrar", "📝 Notas de Crédito", "📄 Cotizaciones"
    ])

    # ── Ventas List ───────────────────────────────────────────────────────────
    with tab_ventas:
        data, err = api.list_ventas()
        if err:
            notify_error("No se pudieron cargar las ventas", {"details": str(err)})
        else:
            ventas = results(data)
            if not ventas:
                st.info("No hay ventas registradas. Crea una en la pestaña '➕ Nueva Venta'.")
            else:
                df = pd.DataFrame(ventas)
                display_cols = [c for c in ["numero", "cliente_nombre", "fecha", "total", "estado"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)
                st.caption(f"Total: {len(ventas)} ventas")

                for v in ventas:
                    label = f"**{v.get('numero', '')}** — {v.get('fecha', '')} — {fmt(v.get('total', 0), '₲ ')} — {v.get('estado', '')}"
                    with st.expander(label):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Cliente:** {v.get('cliente_nombre', v.get('cliente', '-'))}")
                            st.write(f"**Fecha:** {v.get('fecha', '-')}")
                            st.write(f"**Estado:** {v.get('estado', '-')}")
                        with c2:
                            st.write(f"**Subtotal:** {fmt(v.get('subtotal', 0), '₲ ')}")
                            st.write(f"**Impuestos:** {fmt(v.get('impuestos', 0), '₲ ')}")
                            st.write(f"**Total:** {fmt(v.get('total', 0), '₲ ')}")

                        lineas = v.get("lineas", [])
                        if lineas:
                            st.write("**Lineas:**")
                            ldf = pd.DataFrame(lineas)
                            lcols = [c for c in ["producto_nombre", "cantidad", "precio_unitario", "subtotal", "total"] if c in ldf.columns]
                            st.dataframe(ldf[lcols] if lcols else ldf, use_container_width=True, hide_index=True)

                        acol1, acol2 = st.columns(2)
                        with acol1:
                            if v.get("estado") == "borrador":
                                if st.button("✅ Confirmar", key=f"conf_v_{v['id']}"):
                                    result, e = api.confirmar_venta(v["id"])
                                    if e:
                                        notify_error(f"No se pudo confirmar la venta", {"details": str(e)})
                                    else:
                                        notify_success(f"Venta **{v.get('numero')}** confirmada")
                                        st.cache_data.clear()
                                        st.cache_resource.clear()
                                        import time
                                        time.sleep(0.5)
                                        st.rerun()
                        with acol2:
                            if v.get("estado") in ("borrador", "confirmada"):
                                if st.button("❌ Anular", key=f"anul_v_{v['id']}"):
                                    result, e = api.anular_venta(v["id"])
                                    if e:
                                        notify_error(f"No se pudo anular la venta", {"details": str(e)})
                                    else:
                                        notify_success(f"Venta **{v.get('numero')}** anulada")
                                        st.cache_data.clear()
                                        st.cache_resource.clear()
                                        import time
                                        time.sleep(0.5)
                                        st.rerun()

    # ── Nueva Venta ───────────────────────────────────────────────────────────
    with tab_nueva:
        # Clear cache to ensure fresh data from products updates
        st.cache_data.clear()
        
        cli_data, cli_err = api.list_clientes()
        clientes = results(cli_data)
        prod_data, prod_err = api.list_productos()
        productos = results(prod_data)

        if not clientes:
            st.warning("Necesitas al menos un cliente para crear una venta. Ve a la seccion Clientes.")
        elif not productos:
            st.warning("Necesitas al menos un producto para crear una venta. Ve a la seccion Productos.")
        else:
            st.subheader("Paso 1: Datos de la Venta")
            with st.form("new_venta"):
                col1, col2 = st.columns(2)
                with col1:
                    numero = st.text_input("Numero de Factura *", placeholder="FAC-001")
                    cli_opts = {c["id"]: f"{c.get('ruc','')} - {c.get('nombre','')}" for c in clientes}
                    cliente_id = st.selectbox("Cliente *", options=list(cli_opts.keys()),
                                              format_func=lambda x: cli_opts[x])
                with col2:
                    fecha = st.date_input("Fecha *")
                    metodo = st.selectbox("Metodo de Pago", ["", "efectivo", "transferencia", "cheque", "tarjeta"])

                notas = st.text_area("Notas", placeholder="Observaciones...")

                if st.form_submit_button("Crear Venta (Borrador)", type="primary", use_container_width=True):
                    if not numero:
                        notify_error("El número de factura es obligatorio")
                    else:
                        payload = {
                            "numero": numero, "cliente": cliente_id,
                            "fecha": str(fecha), "metodo_pago": metodo,
                            "notas": notas,
                        }
                        result, err = api.create_venta(payload)
                        if err:
                            notify_error(f"No se pudo crear la venta", {"error": str(err), "payload": payload})
                        else:
                            notify_success(f"Venta **{numero}** creada en borrador")
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            import time
                            time.sleep(0.5)
                            st.session_state["venta_nueva_id"] = result.get("id")
                            st.rerun()

            # Add lines to existing draft venta
            venta_id = st.session_state.get("venta_nueva_id")
            if venta_id:
                st.divider()
                st.subheader("Paso 2: Agregar Lineas")

                # Show current venta details
                venta_detail, _ = api.get_venta(venta_id)
                if venta_detail:
                    lineas = venta_detail.get("lineas", [])
                    if lineas:
                        st.write(f"**Lineas actuales:** {len(lineas)}")
                        ldf = pd.DataFrame(lineas)
                        lcols = [c for c in ["producto_nombre", "cantidad", "precio_unitario", "condicion_iva", "subtotal", "impuesto_monto", "total"] if c in ldf.columns]
                        st.dataframe(ldf[lcols] if lcols else ldf, use_container_width=True, hide_index=True)
                    
                    # Mostrar desglose de totales en tiempo real
                    t1, t2, t3 = st.columns(3)
                    with t1:
                        st.metric("Subtotal", fmt(venta_detail.get('subtotal', 0), '₲ '))
                    with t2:
                        st.metric("Impuestos", fmt(venta_detail.get('impuestos', 0), '₲ '))
                    with t3:
                        st.metric("Total", fmt(venta_detail.get('total', 0), '₲ '))

                with st.form("add_line"):
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                    with col1:
                        prod_opts = {p["id"]: f"{p.get('sku','')} - {p.get('nombre','')}" for p in productos}
                        prod_id = st.selectbox("Producto", options=list(prod_opts.keys()),
                                               format_func=lambda x: prod_opts[x])
                    with col2:
                        cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
                    with col3:
                        precio = st.number_input("Precio Unitario", min_value=0, value=0, step=1000)
                    with col4:
                        condicion_iva = st.selectbox(
                            "Condición IVA",
                            options=['gravada_10', 'gravada_5', 'exenta'],
                            format_func=lambda x: {'gravada_10': 'Gravada 10%', 'gravada_5': 'Gravada 5%', 'exenta': 'Exenta'}[x],
                        )

                    if st.form_submit_button("Agregar Linea", use_container_width=True):
                        payload = {
                            "producto": prod_id,
                            "cantidad": str(cantidad),
                            "precio_unitario": str(precio),
                            "condicion_iva": condicion_iva,
                        }
                        result, err = api.agregar_linea_venta(venta_id, payload)
                        if err:
                            notify_error(f"No se pudo agregar la línea", {"error": str(err), "payload": payload})
                        else:
                            notify_success("Línea agregada correctamente")
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            import time
                            time.sleep(0.5)
                            st.rerun()

                st.divider()
                st.subheader("Paso 3: Confirmar y Cobro")
                
                # Opción de marcar como pagada
                col_pagada, col_fecha = st.columns(2)
                with col_pagada:
                    esta_pagada = st.checkbox(
                        "✅ Esta factura ya fue pagada completamente",
                        value=False,
                        key="venta_pagada_check"
                    )
                with col_fecha:
                    if esta_pagada:
                        fecha_pago = st.date_input(
                            "Fecha del Pago",
                            key="venta_fecha_pago"
                        )
                
                # Detalles de pago si está pagada
                if esta_pagada:
                    st.info("💳 Se registrará automáticamente el pago al confirmar")
                    col_metodo, col_ref = st.columns(2)
                    with col_metodo:
                        metodo_pago = st.selectbox(
                            "Método de Pago",
                            ["transferencia", "efectivo", "cheque", "tarjeta", "otro"],
                            key="venta_metodo_pago_confirm"
                        )
                    with col_ref:
                        referencia_pago = st.text_input(
                            "Referencia (opcional)",
                            placeholder="Número de transacción, comprobante...",
                            key="venta_ref_confirm"
                        )
                    
                    obs_pago_confirm = st.text_area(
                        "Observaciones del Pago",
                        placeholder="Ej: Pago completo en primer contacto...",
                        key="venta_obs_pago_confirm"
                    )
                
                col_conf, col_clear = st.columns(2)
                with col_conf:
                    if st.button("✅ Confirmar Venta", type="primary", use_container_width=True):
                        # Confirmar venta
                        result, err = api.confirmar_venta(venta_id)
                        if err:
                            notify_error(f"No se pudo confirmar la venta", {"error": str(err)})
                        else:
                            # Si está pagada, registrar el pago
                            if esta_pagada:
                                venta_detail, _ = api.get_venta(venta_id)
                                if venta_detail:
                                    pago_payload = {
                                        "venta": venta_id,
                                        "cliente": venta_detail.get("cliente_id") or venta_detail.get("cliente", ""),
                                        "monto": str(venta_detail.get("total", 0)),
                                        "metodo": metodo_pago,
                                        "referencia": referencia_pago,
                                    }
                                    pago_result, pago_err = api.create_pago(pago_payload)
                                    if pago_err:
                                        notify_warning(f"Venta confirmada pero error registrando pago: {pago_err}")
                                    else:
                                        # Auto-confirmar para generar asiento
                                        pago_id = pago_result.get("id")
                                        if pago_id:
                                            api.confirmar_pago(pago_id)
                                        notify_success("Venta confirmada y pagada registrada completamente!")
                            else:
                                notify_success("Venta confirmada! Se generó la cuenta por cobrar")
                            
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            import time
                            time.sleep(0.5)
                            st.session_state.pop("venta_nueva_id", None)
                            st.rerun()
                with col_clear:
                    if st.button("🔄 Limpiar", use_container_width=True):
                        st.session_state.pop("venta_nueva_id", None)
                        st.rerun()

    # ── Carga Rápida ─────────────────────────────────────────────────────────
    with tab_rapida:
        st.subheader("⚡ Carga Rápida — Venta Confirmada y Pagada")
        st.info("Crea una venta ya confirmada (y opcionalmente pagada) en un solo paso. Ideal para registrar ventas ya realizadas.")
        
        cli_data_r, _ = api.list_clientes()
        clientes_r = results(cli_data_r)
        prod_data_r, _ = api.list_productos()
        productos_r = results(prod_data_r)

        if not clientes_r:
            st.warning("Necesitas al menos un cliente.")
        elif not productos_r:
            st.warning("Necesitas al menos un producto.")
        else:
            # Datos de la venta
            col1, col2 = st.columns(2)
            with col1:
                cr_numero = st.text_input("Número de Factura *", placeholder="FAC-001", key="cr_numero")
                cli_opts_r = {c["id"]: f"{c.get('ruc','')} - {c.get('nombre','')}" for c in clientes_r}
                cr_cliente = st.selectbox("Cliente *", options=list(cli_opts_r.keys()),
                                          format_func=lambda x: cli_opts_r[x], key="cr_cliente")
            with col2:
                cr_fecha = st.date_input("Fecha *", key="cr_fecha")
                cr_metodo = st.selectbox("Método de Pago", ["efectivo", "transferencia", "cheque", "tarjeta", ""], key="cr_metodo")

            cr_pagada = st.checkbox("✅ Esta factura ya fue pagada completamente", value=True, key="cr_pagada")
            
            if cr_pagada:
                cr_col1, cr_col2 = st.columns(2)
                with cr_col1:
                    cr_referencia = st.text_input("Referencia de Pago", placeholder="Nro. comprobante...", key="cr_ref")
                with cr_col2:
                    cr_obs_pago = st.text_input("Observaciones Pago", key="cr_obs_pago")
            
            cr_notas = st.text_area("Notas", placeholder="Observaciones...", key="cr_notas")
            
            st.divider()
            st.subheader("Líneas de la Venta")
            
            # Session state for lines
            if "cr_lineas" not in st.session_state:
                st.session_state["cr_lineas"] = []
            
            prod_opts_r = {p["id"]: f"{p.get('sku','')} - {p.get('nombre','')} (₲ {p.get('precio_unitario', 0):,})" for p in productos_r}
            
            with st.form("cr_add_line"):
                lc1, lc2, lc3, lc4 = st.columns([3, 2, 2, 2])
                with lc1:
                    cr_prod = st.selectbox("Producto", options=list(prod_opts_r.keys()),
                                           format_func=lambda x: prod_opts_r[x], key="cr_prod")
                with lc2:
                    cr_cant = st.number_input("Cantidad", min_value=1, value=1, step=1, key="cr_cant")
                with lc3:
                    cr_precio = st.number_input("Precio Unitario", min_value=0, value=0, step=1000, key="cr_precio")
                with lc4:
                    cr_iva = st.selectbox(
                        "IVA",
                        options=['gravada_10', 'gravada_5', 'exenta'],
                        format_func=lambda x: {'gravada_10': '10%', 'gravada_5': '5%', 'exenta': 'Exenta'}[x],
                        key="cr_iva"
                    )
                
                if st.form_submit_button("➕ Agregar Línea", use_container_width=True):
                    prod_info = next((p for p in productos_r if p["id"] == cr_prod), {})
                    precio_final = cr_precio if cr_precio > 0 else float(prod_info.get('precio_unitario', 0))
                    iva_map = {'gravada_10': 10, 'gravada_5': 5, 'exenta': 0}
                    tasa = iva_map.get(cr_iva, 10)
                    subtotal = cr_cant * precio_final
                    impuesto = subtotal * (tasa / 100)
                    
                    st.session_state["cr_lineas"].append({
                        "producto": cr_prod,
                        "producto_nombre": prod_info.get('nombre', ''),
                        "cantidad": cr_cant,
                        "precio_unitario": precio_final,
                        "condicion_iva": cr_iva,
                        "subtotal": subtotal,
                        "impuesto": impuesto,
                        "total": subtotal + impuesto,
                    })
                    st.rerun()
            
            # Show current lines
            lineas_cr = st.session_state.get("cr_lineas", [])
            if lineas_cr:
                ldf = pd.DataFrame(lineas_cr)
                st.dataframe(
                    ldf[["producto_nombre", "cantidad", "precio_unitario", "condicion_iva", "subtotal", "impuesto", "total"]],
                    use_container_width=True, hide_index=True
                )
                
                # Totals
                total_sub = sum(l["subtotal"] for l in lineas_cr)
                total_imp = sum(l["impuesto"] for l in lineas_cr)
                total_tot = sum(l["total"] for l in lineas_cr)
                
                t1, t2, t3 = st.columns(3)
                with t1:
                    st.metric("Subtotal", fmt(total_sub, '₲ '))
                with t2:
                    st.metric("Impuestos", fmt(total_imp, '₲ '))
                with t3:
                    st.metric("Total", fmt(total_tot, '₲ '))
                
                col_submit, col_clear_lines = st.columns(2)
                with col_submit:
                    if st.button("✅ Registrar Venta", type="primary", use_container_width=True, key="cr_submit"):
                        if not cr_numero:
                            notify_error("El número de factura es obligatorio")
                        else:
                            payload = {
                                "numero": cr_numero,
                                "cliente": cr_cliente,
                                "fecha": str(cr_fecha),
                                "metodo_pago": cr_metodo,
                                "notas": cr_notas,
                                "esta_pagada": cr_pagada,
                                "referencia_pago": cr_referencia if cr_pagada else "",
                                "observaciones_pago": cr_obs_pago if cr_pagada else "",
                                "lineas": [
                                    {
                                        "producto": l["producto"],
                                        "cantidad": l["cantidad"],
                                        "precio_unitario": str(l["precio_unitario"]),
                                        "condicion_iva": l["condicion_iva"],
                                    }
                                    for l in lineas_cr
                                ],
                            }
                            result, err = api.carga_rapida_venta(payload)
                            if err:
                                notify_error(f"Error al registrar venta", {"error": str(err)})
                            else:
                                estado_final = "pagada" if cr_pagada else "confirmada"
                                notify_success(f"Venta **{cr_numero}** registrada como {estado_final}")
                                st.session_state["cr_lineas"] = []
                                st.cache_data.clear()
                                st.cache_resource.clear()
                                import time
                                time.sleep(0.5)
                                st.rerun()
                with col_clear_lines:
                    if st.button("🗑️ Limpiar Líneas", use_container_width=True, key="cr_clear"):
                        st.session_state["cr_lineas"] = []
                        st.rerun()
            else:
                st.info("Agrega al menos una línea para registrar la venta.")

    # ── Cuentas por Cobrar ────────────────────────────────────────────────────
    with tab_cxc:
        resumen, _ = api.get_cxc_resumen()
        if resumen:
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("Total Pendiente", fmt(resumen.get('total_pendiente', 0), '₲ '))
            with c2:
                st.metric("Cantidad CxC", str(resumen.get('cantidad', 0)))
            with c3:
                st.metric("Vencidas", str(resumen.get('cantidad_vencidas', 0)))
            st.divider()

        cxc_data, cxc_err = api.list_cuentas_por_cobrar()
        if cxc_err:
            notify_error("No se pudieron cargar las cuentas por cobrar", {"details": str(cxc_err)})
        else:
            cxc = results(cxc_data)
            if not cxc:
                st.info("No hay cuentas por cobrar.")
            else:
                df = pd.DataFrame(cxc)
                display_cols = [c for c in ["venta_numero", "cliente_nombre", "monto_original", "monto_pagado", "saldo", "fecha_vencimiento", "estado"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)

        with st.expander("⚠️ Cuentas Vencidas"):
            vencidas, v_err = api.get_cxc_vencidas()
            if v_err:
                notify_error("No se pudieron cargar las cuentas vencidas", {"details": str(v_err)})
            else:
                venc_list = results(vencidas) if not isinstance(vencidas, list) else vencidas
                if venc_list:
                    vdf = pd.DataFrame(venc_list)
                    st.dataframe(vdf, use_container_width=True, hide_index=True)
                else:
                    notify_info("No hay cuentas vencidas")

        with st.expander("📊 Aging Report (Antigüedad de Saldos)"):
            aging_data, aging_err = api.get_cxc_aging()
            if aging_err:
                notify_error("No se pudo cargar el aging report", {"details": str(aging_err)})
            elif aging_data:
                ac1, ac2, ac3, ac4, ac5 = st.columns(5)
                with ac1:
                    st.metric("Corriente", fmt(aging_data.get('corriente', 0), '₲ '))
                with ac2:
                    st.metric("0-30 días", fmt(aging_data.get('tramo_0_30', 0), '₲ '))
                with ac3:
                    st.metric("31-60 días", fmt(aging_data.get('tramo_31_60', 0), '₲ '))
                with ac4:
                    st.metric("61-90 días", fmt(aging_data.get('tramo_61_90', 0), '₲ '))
                with ac5:
                    st.metric("90+ días", fmt(aging_data.get('tramo_90_plus', 0), '₲ '))

                total_p = aging_data.get('total_pendiente', 0)
                if total_p and float(total_p) > 0:
                    st.caption(f"Total pendiente: {fmt(total_p, '₲ ')} en {aging_data.get('total_cuentas', 0)} cuentas")

    # ── Notas de Crédito ──────────────────────────────────────────────────────
    with tab_nc:
        st.subheader("Notas de Crédito")
        nc_data, nc_err = api.list_notas_credito()
        if nc_err:
            notify_error("No se pudieron cargar las notas de crédito", {"details": str(nc_err)})
        else:
            notas = results(nc_data)
            if notas:
                df_nc = pd.DataFrame(notas)
                nc_cols = [c for c in ["numero", "venta_numero", "cliente_nombre", "fecha", "motivo", "total", "estado"] if c in df_nc.columns]
                st.dataframe(df_nc[nc_cols] if nc_cols else df_nc, use_container_width=True, hide_index=True)

                for nc in notas:
                    if nc.get("estado") == "borrador":
                        with st.expander(f"NC-{nc.get('numero', '')} (Borrador)"):
                            if st.button("✅ Confirmar NC", key=f"conf_nc_{nc['id']}"):
                                result, e = api.confirmar_nota_credito(nc["id"])
                                if e:
                                    notify_error(f"No se pudo confirmar la NC", {"details": str(e)})
                                else:
                                    notify_success(f"NC **{nc.get('numero')}** confirmada")
                                    st.cache_data.clear()
                                    st.cache_resource.clear()
                                    import time
                                    time.sleep(0.5)
                                    st.rerun()
            else:
                st.info("No hay notas de crédito registradas.")

        st.divider()
        st.subheader("➕ Nueva Nota de Crédito")

        # Cargar ventas confirmadas para vincular
        ventas_data, _ = api.list_ventas()
        ventas_list = results(ventas_data) if ventas_data else []
        ventas_confirmadas = [v for v in ventas_list if v.get("estado") in ("confirmada", "parcial", "facturada")]

        if not ventas_confirmadas:
            st.info("No hay ventas confirmadas para emitir nota de crédito.")
        else:
            with st.form("new_nc"):
                nc_numero = st.text_input("Número NC *", placeholder="NC-001")
                venta_opts = {v["id"]: f"{v.get('numero','')} - {v.get('cliente_nombre','')} - {fmt(v.get('total',0), '₲ ')}" for v in ventas_confirmadas}
                nc_venta_id = st.selectbox("Factura Original *", options=list(venta_opts.keys()),
                                            format_func=lambda x: venta_opts[x])
                nc_motivo = st.selectbox("Motivo", [
                    ("devolucion", "Devolución de mercadería"),
                    ("descuento", "Descuento posterior"),
                    ("bonificacion", "Bonificación"),
                    ("error_facturacion", "Error de facturación"),
                    ("otro", "Otro"),
                ], format_func=lambda x: x[1])
                nc_fecha = st.date_input("Fecha")
                nc_desc = st.text_area("Descripción", placeholder="Detalle del motivo...")

                if st.form_submit_button("Crear NC (Borrador)", type="primary", use_container_width=True):
                    if not nc_numero:
                        notify_error("El número de NC es obligatorio")
                    else:
                        # Buscar cliente de la venta seleccionada
                        venta_sel = next((v for v in ventas_confirmadas if v["id"] == nc_venta_id), None)
                        payload = {
                            "numero": nc_numero,
                            "venta_original": nc_venta_id,
                            "cliente": venta_sel.get("cliente") if venta_sel else "",
                            "fecha": str(nc_fecha),
                            "motivo": nc_motivo[0],
                            "descripcion": nc_desc,
                        }
                        result, err = api.create_nota_credito(payload)
                        if err:
                            notify_error(f"No se pudo crear la NC", {"error": str(err)})
                        else:
                            notify_success(f"NC **{nc_numero}** creada en borrador")
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            import time
                            time.sleep(0.5)
                            st.rerun()

    # ── Cotizaciones ──────────────────────────────────────────────────────────
    with tab_cotiz:
        cot_data, cot_err = api.list_cotizaciones()
        if cot_err:
            notify_error("No se pudieron cargar las cotizaciones", {"details": str(cot_err)})
        else:
            cotizaciones = results(cot_data)
            if not cotizaciones:
                st.info("No hay cotizaciones registradas.")
            else:
                df = pd.DataFrame(cotizaciones)
                display_cols = [c for c in ["numero", "fecha", "cliente_nombre", "total", "estado"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)
