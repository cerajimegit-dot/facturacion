"""Ventas, Cotizaciones and Cuentas por Cobrar page."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results, fmt


def render():
    st.header("🧾 Ventas")

    tab_ventas, tab_nueva, tab_cxc, tab_cotiz = st.tabs([
        "📋 Ventas", "➕ Nueva Venta", "💳 Cuentas por Cobrar", "📄 Cotizaciones"
    ])

    # ── Ventas List ───────────────────────────────────────────────────────────
    with tab_ventas:
        data, err = api.list_ventas()
        if err:
            st.error(f"Error: {err}")
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
                                        st.error(f"Error: {e}")
                                    else:
                                        st.success("Venta confirmada.")
                                        st.rerun()
                        with acol2:
                            if v.get("estado") in ("borrador", "confirmada"):
                                if st.button("❌ Anular", key=f"anul_v_{v['id']}"):
                                    result, e = api.anular_venta(v["id"])
                                    if e:
                                        st.error(f"Error: {e}")
                                    else:
                                        st.success("Venta anulada.")
                                        st.rerun()

    # ── Nueva Venta ───────────────────────────────────────────────────────────
    with tab_nueva:
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
                        st.error("El numero de factura es obligatorio.")
                    else:
                        payload = {
                            "numero": numero, "cliente": cliente_id,
                            "fecha": str(fecha), "metodo_pago": metodo,
                            "notas": notas,
                        }
                        result, err = api.create_venta(payload)
                        if err:
                            st.error(f"Error: {err}")
                        else:
                            st.success(f"✅ Venta **{numero}** creada en borrador.")
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
                        lcols = [c for c in ["producto_nombre", "cantidad", "precio_unitario", "subtotal", "total"] if c in ldf.columns]
                        st.dataframe(ldf[lcols] if lcols else ldf, use_container_width=True, hide_index=True)
                    st.write(f"**Total actual:** {fmt(venta_detail.get('total', 0), '₲ ')}")

                with st.form("add_line"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        prod_opts = {p["id"]: f"{p.get('sku','')} - {p.get('nombre','')}" for p in productos}
                        prod_id = st.selectbox("Producto", options=list(prod_opts.keys()),
                                               format_func=lambda x: prod_opts[x])
                    with col2:
                        cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
                    with col3:
                        precio = st.number_input("Precio Unitario", min_value=0, value=0, step=1000)

                    if st.form_submit_button("Agregar Linea", use_container_width=True):
                        payload = {
                            "producto": prod_id,
                            "cantidad": str(cantidad),
                            "precio_unitario": str(precio),
                        }
                        result, err = api.agregar_linea_venta(venta_id, payload)
                        if err:
                            st.error(f"Error: {err}")
                        else:
                            st.success("Linea agregada.")
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
                            st.error(f"Error: {err}")
                        else:
                            # Si está pagada, registrar el pago
                            if esta_pagada:
                                venta_detail, _ = api.get_venta(venta_id)
                                if venta_detail:
                                    pago_payload = {
                                        "venta": venta_id,
                                        "monto": str(venta_detail.get("total", 0)),
                                        "metodo_pago": metodo_pago,
                                        "referencia": referencia_pago,
                                        "observaciones": obs_pago_confirm,
                                    }
                                    pago_result, pago_err = api.create_registro_pago(pago_payload)
                                    if pago_err:
                                        st.warning(f"Venta confirmada pero error registrando pago: {pago_err}")
                                    else:
                                        st.success("✅ Venta confirmada y pagada registrada completamente!")
                            else:
                                st.success("✅ Venta confirmada! Se genero la cuenta por cobrar.")
                            
                            st.session_state.pop("venta_nueva_id", None)
                            st.rerun()
                with col_clear:
                    if st.button("🔄 Limpiar", use_container_width=True):
                        st.session_state.pop("venta_nueva_id", None)
                        st.rerun()

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
            st.error(f"Error: {cxc_err}")
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
                st.error(f"Error: {v_err}")
            else:
                venc_list = results(vencidas) if not isinstance(vencidas, list) else vencidas
                if venc_list:
                    vdf = pd.DataFrame(venc_list)
                    st.dataframe(vdf, use_container_width=True, hide_index=True)
                else:
                    st.success("No hay cuentas vencidas.")

    # ── Cotizaciones ──────────────────────────────────────────────────────────
    with tab_cotiz:
        cot_data, cot_err = api.list_cotizaciones()
        if cot_err:
            st.error(f"Error: {cot_err}")
        else:
            cotizaciones = results(cot_data)
            if not cotizaciones:
                st.info("No hay cotizaciones registradas.")
            else:
                df = pd.DataFrame(cotizaciones)
                display_cols = [c for c in ["numero", "fecha", "cliente_nombre", "total", "estado"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)
