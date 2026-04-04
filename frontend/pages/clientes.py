"""Clientes CRUD page."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results, fmt


def render():
    st.header("👥 Clientes")

    tab_list, tab_new, tab_edit = st.tabs(["📋 Lista de Clientes", "➕ Nuevo Cliente", "✏️ Editar"])

    # ── List ──────────────────────────────────────────────────────────────────
    with tab_list:
        search = st.text_input("🔍 Buscar", placeholder="Nombre, RUC o email...", key="cli_search")

        data, err = api.list_clientes(search=search)
        if err:
            st.error(f"Error: {err}")
        else:
            clientes = results(data)

            if not clientes:
                st.info("No hay clientes registrados. Crea uno en la pestaña '➕ Nuevo Cliente'.")
            else:
                df = pd.DataFrame(clientes)
                display_cols = [c for c in ["nombre", "ruc", "tipo_cliente", "email", "telefono", "activo"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)
                st.caption(f"Total: {len(clientes)} clientes")

                for cli in clientes:
                    with st.expander(f"**{cli.get('nombre', '')}** — {cli.get('ruc', '')}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**RUC:** {cli.get('ruc', '-')}")
                            st.write(f"**Tipo:** {cli.get('tipo_cliente', '-')}")
                            st.write(f"**Email:** {cli.get('email', '-')}")
                            st.write(f"**Teléfono:** {cli.get('telefono', '-')}")
                        with c2:
                            st.write(f"**Límite Crédito:** {fmt(cli.get('limite_credito', 0), '₲ ')}")
                            st.write(f"**Activo:** {'✅' if cli.get('activo', True) else '❌'}")

                        if st.button("🗑️ Eliminar", key=f"del_cli_{cli['id']}"):
                            ok, e = api.delete_cliente(cli["id"])
                            if ok:
                                st.success("Cliente eliminado.")
                                st.rerun()
                            else:
                                st.error(f"Error: {e}")

    # ── New ───────────────────────────────────────────────────────────────────
    with tab_new:
        with st.form("new_cliente"):
            col1, col2 = st.columns(2)
            with col1:
                nombre = st.text_input("Nombre *", placeholder="Juan Pérez")
                ruc = st.text_input("RUC *", placeholder="80012345-6")
                tipo = st.selectbox("Tipo", ["persona", "empresa"])
                telefono = st.text_input("Teléfono", placeholder="+595 981 123456")
            with col2:
                email = st.text_input("Email", placeholder="cliente@email.com")
                sector = st.text_input("Sector", placeholder="Comercio")
                zona = st.text_input("Zona", placeholder="Asunción Centro")
                limite_credito = st.number_input("Límite de Crédito", min_value=0, value=0, step=100000)

            direccion = st.text_area("Dirección de Facturación", placeholder="Calle 123, Asunción")
            observaciones = st.text_area("Observaciones", placeholder="Notas adicionales...")

            if st.form_submit_button("Crear Cliente", type="primary", use_container_width=True):
                if not nombre:
                    st.error("Nombre es obligatorio.")
                else:
                    payload = {
                        "nombre": nombre, "ruc": ruc, "tipo_cliente": tipo,
                        "telefono": telefono, "email": email, "sector": sector,
                        "zona": zona, "limite_credito": str(limite_credito),
                        "direccion_facturacion": direccion,
                        "observaciones": observaciones,
                    }
                    result, err = api.create_cliente(payload)
                    if err:
                        st.error(f"Error: {err}")
                    else:
                        st.success(f"✅ Cliente **{nombre}** creado.")
                        st.rerun()

    # ── Edit ──────────────────────────────────────────────────────────────────
    with tab_edit:
        data, err = api.list_clientes()
        if err:
            st.error(f"Error: {err}")
        else:
            clientes = results(data)
            if not clientes:
                st.info("No hay clientes para editar.")
            else:
                cliente_options = {c["nombre"]: c for c in clientes}
                selected_name = st.selectbox("Selecciona Cliente para Editar", options=cliente_options.keys(), key="edit_cliente_select")
                
                if selected_name:
                    cli = cliente_options[selected_name]
                    
                    with st.form("edit_cliente"):
                        col1, col2 = st.columns(2)
                        with col1:
                            nombre = st.text_input("Nombre", value=cli.get("nombre", ""))
                            ruc = st.text_input("RUC", value=cli.get("ruc", ""))
                            tipo = st.selectbox("Tipo", ["persona", "empresa"], index=0 if cli.get("tipo_cliente") == "persona" else 1)
                            telefono = st.text_input("Teléfono", value=cli.get("telefono", ""))
                        with col2:
                            email = st.text_input("Email", value=cli.get("email", ""))
                            sector = st.text_input("Sector", value=cli.get("sector", ""))
                            zona = st.text_input("Zona", value=cli.get("zona", ""))
                            limite_credito = st.number_input("Límite de Crédito", min_value=0, value=int(cli.get("limite_credito", 0)), step=100000)

                        direccion = st.text_area("Dirección de Facturación", value=cli.get("direccion_facturacion", ""))
                        observaciones = st.text_area("Observaciones", value=cli.get("observaciones", ""))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            activo = st.checkbox("Activo", value=cli.get("activo", True))

                        if st.form_submit_button("💾 Guardar Cambios", type="primary", use_container_width=True):
                            payload = {
                                "nombre": nombre, "ruc": ruc, "tipo_cliente": tipo,
                                "telefono": telefono, "email": email, "sector": sector,
                                "zona": zona, "limite_credito": str(limite_credito),
                                "direccion_facturacion": direccion,
                                "observaciones": observaciones, "activo": activo,
                            }
                            result, err = api.update_cliente(cli["id"], payload)
                            if err:
                                st.error(f"Error: {err}")
                            else:
                                st.success(f"✅ Cliente **{nombre}** actualizado.")
                                st.rerun()
