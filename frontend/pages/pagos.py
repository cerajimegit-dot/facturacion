"""Pagos management page."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results, fmt, notify_success, notify_error, notify_info, show_session_notifications


def render():
    show_session_notifications()
    st.header("💰 Pagos")

    tab_list, tab_new = st.tabs(["📋 Pagos Registrados", "➕ Nuevo Pago"])

    # ── List ──────────────────────────────────────────────────────────────────
    with tab_list:
        data, err = api.list_pagos()
        if err:
            notify_error("No se pudieron cargar los pagos", {"details": str(err)})
        else:
            pagos = results(data)
            if not pagos:
                st.info("No hay pagos registrados.")
            else:
                df = pd.DataFrame(pagos)
                display_cols = [c for c in ["fecha", "venta_numero", "cliente_nombre", "monto", "metodo", "estado"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)
                st.caption(f"Total: {len(pagos)} pagos")

                for pago in pagos:
                    with st.expander(f"Pago — {fmt(pago.get('monto', 0), '₲ ')} — {pago.get('fecha', '')}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**Venta:** {pago.get('venta_numero', pago.get('venta', '-'))}")
                            st.write(f"**Monto:** {fmt(pago.get('monto', 0), '₲ ')}")
                            st.write(f"**Metodo:** {pago.get('metodo', '-')}")
                        with c2:
                            st.write(f"**Referencia:** {pago.get('referencia', '-')}")
                            st.write(f"**Estado:** {pago.get('estado', '-')}")
                            st.write(f"**Fecha:** {pago.get('fecha', '-')}")

                        if pago.get("estado") == "pendiente":
                            if st.button("✅ Confirmar Pago", key=f"conf_p_{pago['id']}"):
                                result, e = api.confirmar_pago(pago["id"])
                                if e:
                                    notify_error("No se pudo confirmar el pago", {"details": str(e)})
                                else:
                                    notify_success(f"Pago de ₵ {fmt(pago.get('monto', 0), '')} confirmado")
                                    st.cache_data.clear()
                                    st.cache_resource.clear()
                                    import time
                                    time.sleep(0.5)
                                    st.rerun()

    # ── New Payment ───────────────────────────────────────────────────────────
    with tab_new:
        ventas_data, _ = api.list_ventas()
        ventas = results(ventas_data)
        ventas_confirmadas = [v for v in ventas if v.get("estado") in ("confirmada", "parcial")]

        if not ventas_confirmadas:
            st.warning("No hay ventas confirmadas pendientes de pago. Primero crea y confirma una venta.")
        else:
            with st.form("new_pago"):
                v_opts = {v["id"]: f"{v.get('numero','')} — {fmt(v.get('total', 0), '₲ ')} ({v.get('cliente_nombre', '')})" for v in ventas_confirmadas}
                venta_id = st.selectbox("Venta *", options=list(v_opts.keys()),
                                         format_func=lambda x: v_opts[x])

                col1, col2 = st.columns(2)
                with col1:
                    monto = st.number_input("Monto *", min_value=0, value=0, step=10000)
                    metodo = st.selectbox("Metodo de Pago", ["efectivo", "transferencia", "cheque", "tarjeta"])
                with col2:
                    fecha = st.date_input("Fecha *")
                    referencia = st.text_input("Referencia", placeholder="Nro. de cheque, transferencia, etc.")

                notas = st.text_area("Notas", placeholder="Observaciones...")

                if st.form_submit_button("Registrar Pago", type="primary", use_container_width=True):
                    if monto <= 0:
                        notify_error("El monto debe ser mayor a 0")
                    else:
                        payload = {
                            "venta": venta_id, "monto": str(monto),
                            "metodo": metodo, "fecha": str(fecha),
                            "referencia": referencia, "notas": notas,
                        }
                        result, err = api.create_pago(payload)
                        if err:
                            notify_error("No se pudo registrar el pago", {"error": str(err), "payload": payload})
                        else:
                            notify_success(f"Pago de ₵ {monto:,} registrado correctamente")
                            pago_id = result.get("id")
                            if pago_id:
                                conf, cerr = api.confirmar_pago(pago_id)
                                if not cerr:
                                    notify_success("Pago confirmado automáticamente")
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            import time
                            time.sleep(0.5)
                            st.rerun()
