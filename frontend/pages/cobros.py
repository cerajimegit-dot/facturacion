"""Pagos partial payments tracking page."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results, fmt, notify_success, notify_error, notify_info, show_session_notifications
from datetime import datetime


def render():
    show_session_notifications()
    st.header("💰 Cobros Parciales")
    st.write("Registra pagos parciales y observaciones de avance de cobro")

    tab_ventas, tab_registros = st.tabs(["📋 Facturas", "📝 Registros de Pago"])

    # ── Ventas con saldo pendiente ────────────────────────────────────────────
    with tab_ventas:
        st.subheader("Facturas con Saldo Pendiente")
        
        data, err = api.list_ventas(estado="parcial")
        if err:
            notify_error("No se pudieron cargar las facturas con saldo pendiente", {"details": str(err)})
        else:
            ventas = results(data) if data else []
            
            # Also get pending ventas
            data_pend, err_pend = api.list_ventas(estado="confirmada")
            if not err_pend and data_pend:
                ventas_pend = results(data_pend) if data_pend else []
                ventas.extend(ventas_pend)
            
            if not ventas:
                st.info("No hay facturas con saldo pendiente.")
            else:
                # Mostrar tabla
                df_display = pd.DataFrame([
                    {
                        "Factura": v.get("numero", ""),
                        "Cliente": v.get("cliente_nombre", ""),
                        "Total": fmt(v.get("total", 0), "₲ "),
                        "Pagado": fmt(v.get("total_pagado", 0), "₲ "),
                        "Pendiente": fmt(v.get("saldo_pendiente", 0), "₲ "),
                        "Estado": v.get("estado", "").title(),
                    }
                    for v in ventas
                ])
                
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                
                # Seleccionar factura para registrar pago
                st.divider()
                st.subheader("💳 Registrar Pago Parcial")
                
                venta_options = {f"FAC {v['numero']} - {v['cliente_nombre']}: ₲ {v['saldo_pendiente']}": v for v in ventas}
                selected_venta = st.selectbox("Selecciona Factura", options=venta_options.keys(), key="venta_pago_select")
                
                if selected_venta:
                    venta = venta_options[selected_venta]
                    
                    # Convert saldo_pendiente (string from API) to int for max_value
                    saldo_pendiente = float(venta.get("saldo_pendiente", 0) or 0)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        monto_pago = st.number_input(
                            "Monto a Cobrar",
                            min_value=0,
                            max_value=int(saldo_pendiente),
                            value=0,
                            step=1000,
                            key="monto_pago_input"
                        )
                        metodo = st.selectbox(
                            "Método de Pago",
                            ["transferencia", "efectivo", "cheque", "tarjeta", "otro"],
                            key="metodo_pago_select"
                        )
                    
                    with col2:
                        referencia = st.text_input(
                            "Referencia (opcional)",
                            placeholder="Número de transacción, comprobante...",
                            key="referencia_pago_input"
                        )
                    
                    observaciones = st.text_area(
                        "Observaciones",
                        placeholder="Ej: Pago por avance del 50% de obra...",
                        key="obs_pago_textarea"
                    )
                    
                    if st.button("✅ Registrar Pago", type="primary", use_container_width=True):
                        if monto_pago <= 0:
                            notify_error("El monto debe ser mayor a 0")
                        else:
                            # Crear Pago en módulo pagos (con workflow completo y asiento contable)
                            payload = {
                                "venta": venta["id"],
                                "cliente": venta.get("cliente_id") or venta.get("cliente", {}).get("id", ""),
                                "monto": str(monto_pago),
                                "metodo": metodo,
                                "referencia": referencia,
                            }
                            result, err = api.create_pago(payload)
                            if err:
                                notify_error(f"No se pudo registrar el pago", {"error": str(err), "payload": payload})
                            else:
                                # Auto-confirmar para generar asiento contable
                                pago_id = result.get("id")
                                if pago_id:
                                    conf_result, conf_err = api.confirmar_pago(pago_id)
                                    if conf_err:
                                        notify_error(f"Pago creado pero no se pudo confirmar", {"error": str(conf_err)})
                                    else:
                                        notify_success(f"Pago de ₵ {monto_pago:,} registrado y confirmado")
                                else:
                                    notify_success(f"Pago de ₵ {monto_pago:,} registrado correctamente")
                                st.cache_data.clear()
                                st.cache_resource.clear()
                                import time
                                time.sleep(0.5)
                                st.rerun()
                
                # Actualizar observaciones de cobro
                st.divider()
                st.subheader("📝 Observaciones de Cobro")
                
                venta_obs_sel = st.selectbox(
                    "Selecciona factura para actualizar observaciones",
                    options=venta_options.keys(),
                    key="venta_obs_select"
                )
                
                if venta_obs_sel:
                    venta_obs = venta_options[venta_obs_sel]
                    
                    obs_actual = venta_obs.get("observaciones_cobro", "")
                    obs_nueva = st.text_area(
                        "Observaciones de Avance",
                        value=obs_actual,
                        placeholder="Ej: Primer pago al inicio de obra, segundo pago al 50%, final al terminar...",
                        key="obs_cobro_textarea"
                    )
                    
                    if st.button("💾 Guardar Observaciones", use_container_width=True):
                        payload = {"observaciones_cobro": obs_nueva}
                        result, err = api.update_venta(venta_obs["id"], payload)
                        if err:
                            notify_error(f"No se pudieron guardar las observaciones", {"details": str(err)})
                        else:
                            notify_success("Observaciones de cobro guardadas correctamente")
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            import time
                            time.sleep(0.5)
                            st.rerun()

    # ── Registros de pago ─────────────────────────────────────────────────────
    with tab_registros:
        st.subheader("Historial de Pagos Registrados")
        
        # Filtros
        col1, col2 = st.columns(2)
        with col1:
            metodo_filter = st.selectbox(
                "Filtrar por Método",
                ["todos", "transferencia", "efectivo", "cheque", "tarjeta", "otro"],
                key="metodo_filter"
            )
        with col2:
            estado_filter = st.selectbox(
                "Filtrar por Estado de Factura",
                ["todos", "confirmada", "parcial", "pagada"],
                key="estado_filter_pagos"
            )
        
        # Cargar pagos (usando módulo Pago con asientos contables)
        data, err = api.list_pagos()
        if err:
            notify_error("No se pudieron cargar los registros de pago", {"details": str(err)})
        else:
            pagos = results(data) if data else []
            
            # Apply filters
            if metodo_filter != "todos":
                pagos = [p for p in pagos if p.get("metodo", "") == metodo_filter]
            
            if not pagos:
                st.info("No hay registros de pago.")
            else:
                # Filtrar por estado si es necesario
                if estado_filter != "todos":
                    pagos = [p for p in pagos if p.get("venta_detalle", {}).get("estado") == estado_filter]
                
                # Mostrar tabla
                df_pagos = pd.DataFrame([
                    {
                        "Fecha": p.get("fecha", "")[:10],
                        "Factura": p.get("venta_detalle", {}).get("numero", p.get("venta_numero", "")),
                        "Monto": fmt(p.get("monto", 0), "₲ "),
                        "Método": p.get("metodo", "").title(),
                        "Estado": p.get("estado", "").title(),
                        "Referencia": p.get("referencia", "-"),
                    }
                    for p in pagos
                ])
                
                st.dataframe(df_pagos, use_container_width=True, hide_index=True)
                st.caption(f"Total: {len(pagos)} pagos registrados")
                
                # Expandibles para ver detalles
                st.divider()
                venta_num_key = lambda p: p.get("venta_detalle", {}).get("numero", p.get("venta_numero", ""))
                for pago in pagos[:10]:  # Mostrar detalles de últimos 10
                    with st.expander(f"**{venta_num_key(pago)}** - {fmt(pago['monto'], '₲ ')} ({pago.get('fecha', '')[:10]})"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Factura:** {venta_num_key(pago)}")
                            st.write(f"**Monto:** {fmt(pago['monto'], '₲ ')}")
                            st.write(f"**Método:** {pago.get('metodo', '').title()}")
                            st.write(f"**Estado:** {pago.get('estado', '').title()}")
                        with col2:
                            st.write(f"**Fecha:** {pago.get('fecha', '')[:10]}")
                            if pago.get('referencia'):
                                st.write(f"**Referencia:** {pago['referencia']}")
