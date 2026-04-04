"""Pagos partial payments tracking page."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results, fmt
from datetime import datetime


def render():
    st.header("💰 Cobros Parciales")
    st.write("Registra pagos parciales y observaciones de avance de cobro")

    tab_ventas, tab_registros = st.tabs(["📋 Facturas", "📝 Registros de Pago"])

    # ── Ventas con saldo pendiente ────────────────────────────────────────────
    with tab_ventas:
        st.subheader("Facturas con Saldo Pendiente")
        
        data, err = api.list_ventas(estado="parcial")
        if err:
            st.error(f"Error: {err}")
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
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        monto_pago = st.number_input(
                            "Monto a Cobrar",
                            min_value=0,
                            max_value=int(venta.get("saldo_pendiente", 0)),
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
                            st.error("El monto debe ser mayor a 0.")
                        else:
                            payload = {
                                "venta": venta["id"],
                                "monto": str(monto_pago),
                                "metodo_pago": metodo,
                                "referencia": referencia,
                                "observaciones": observaciones,
                            }
                            result, err = api.create_registro_pago(payload)
                            if err:
                                st.error(f"Error al registrar pago: {err}")
                            else:
                                st.success(f"✅ Pago de ₲ {monto_pago:,} registrado correctamente")
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
                            st.error(f"Error: {err}")
                        else:
                            st.success("✅ Observaciones guardadas")
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
        
        # Cargar pagos
        filters = {}
        if metodo_filter != "todos":
            filters["metodo_pago"] = metodo_filter
        
        data, err = api.list_registro_pagos(**filters)
        if err:
            st.error(f"Error: {err}")
        else:
            pagos = results(data) if data else []
            
            if not pagos:
                st.info("No hay registros de pago.")
            else:
                # Filtrar por estado si es necesario
                if estado_filter != "todos":
                    pagos = [p for p in pagos if p.get("venta", {}).get("estado") == estado_filter]
                
                # Mostrar tabla
                df_pagos = pd.DataFrame([
                    {
                        "Fecha": p.get("fecha_pago", "")[:10],
                        "Factura": p.get("venta_numero", ""),
                        "Monto": fmt(p.get("monto", 0), "₲ "),
                        "Método": p.get("metodo_pago", "").title(),
                        "Referencia": p.get("referencia", "-"),
                        "Observaciones": p.get("observaciones", "")[:50] + "..." if len(p.get("observaciones", "")) > 50 else p.get("observaciones", ""),
                    }
                    for p in pagos
                ])
                
                st.dataframe(df_pagos, use_container_width=True, hide_index=True)
                st.caption(f"Total: {len(pagos)} pagos registrados")
                
                # Expandibles para ver detalles
                st.divider()
                for pago in pagos[:10]:  # Mostrar detalles de últimos 10
                    with st.expander(f"**{pago['venta_numero']}** - {fmt(pago['monto'], '₲ ')} ({pago['fecha_pago'][:10]})"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**Factura:** {pago['venta_numero']}")
                            st.write(f"**Monto:** {fmt(pago['monto'], '₲ ')}")
                            st.write(f"**Método:** {pago['metodo_pago'].title()}")
                        with col2:
                            st.write(f"**Fecha:** {pago['fecha_pago'][:10]}")
                            if pago.get('referencia'):
                                st.write(f"**Referencia:** {pago['referencia']}")
                        
                        if pago.get('observaciones'):
                            st.info(f"**Observaciones:** {pago['observaciones']}")
