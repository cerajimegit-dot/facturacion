"""Empresas management page."""
import streamlit as st
import api_client as api
from helpers import results, notify_success, notify_error, notify_info, show_session_notifications


def render():
    show_session_notifications()
    st.header("🏢 Empresas")

    # ── Load empresas ─────────────────────────────────────────────────────────
    data, err = api.list_empresas()
    if err:
        notify_error("No se pudieron cargar las empresas", {"details": str(err)})
        return

    empresas = results(data)

    # ── Active empresa selector ───────────────────────────────────────────────
    if empresas:
        st.subheader("Seleccionar Empresa Activa")
        options = {e["id"]: f"{e.get('codigo', '')} - {e.get('nombre', '')}" for e in empresas}
        current_id = (st.session_state.get("empresa_activa") or {}).get("id")

        ids = list(options.keys())
        idx = ids.index(current_id) if current_id in ids else 0

        selected_id = st.selectbox(
            "Empresa activa", options=ids,
            format_func=lambda x: options[x], index=idx,
            key="empresa_selector",
        )

        if selected_id:
            selected = next((e for e in empresas if e["id"] == selected_id), None)
            if selected and (not st.session_state.get("empresa_activa") or
                             st.session_state["empresa_activa"].get("id") != selected_id):
                st.session_state["empresa_activa"] = selected
                st.rerun()

        st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_list, tab_new = st.tabs(["📋 Mis Empresas", "➕ Nueva Empresa"])

    with tab_list:
        if not empresas:
            st.info("No tienes empresas. Crea una nueva en la pestaña '➕ Nueva Empresa'.")
        else:
            for emp in empresas:
                is_active = (st.session_state.get("empresa_activa") or {}).get("id") == emp["id"]
                badge = " ✅ **ACTIVA**" if is_active else ""
                with st.expander(f"**{emp.get('codigo', '')}** — {emp.get('nombre', '')}{badge}"):
                    col_logo, col_info = st.columns([1, 2])
                    with col_logo:
                        # Mostrar logo
                        logo_url = emp.get("logo_url")
                        if logo_url:
                            st.image(logo_url, width=150, caption="Logo Empresa")
                        else:
                            st.info("Sin logo")
                        # Upload logo
                        logo_file = st.file_uploader(
                            "Subir Logo", 
                            type=["png", "jpg", "jpeg"],
                            key=f"logo_{emp['id']}"
                        )
                        if logo_file:
                            ok, err = api.update_empresa_logo(emp["id"], logo_file)
                            if ok:
                                notify_success("Logo actualizado correctamente")
                                st.cache_data.clear()
                                st.cache_resource.clear()
                                import time
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                notify_error("No se pudo actualizar el logo", {"details": str(err)})
                    
                    with col_info:
                        c1, c2 = st.columns(2)
                        with c1:
                            st.write(f"**RUC:** {emp.get('ruc', '-')}")
                            st.write(f"**Teléfono:** {emp.get('telefono', '-')}")
                            st.write(f"**Email:** {emp.get('email', '-')}")
                        with c2:
                            st.write(f"**Dirección:** {emp.get('direccion', '-')}")
                            st.write(f"**Moneda:** {emp.get('moneda_principal', emp.get('moneda', 'PYG'))}")
                            st.write(f"**Activa:** {'Sí' if emp.get('activa', True) else 'No'}")

                    col_a, col_b = st.columns(2)
                    with col_a:
                        if not is_active:
                            if st.button("✅ Activar", key=f"act_{emp['id']}"):
                                st.session_state["empresa_activa"] = emp
                                st.rerun()
                    with col_b:
                        if st.button("🗑️ Eliminar", key=f"del_{emp['id']}", type="secondary"):
                            ok, e = api.delete_empresa(emp["id"])
                            if ok:
                                notify_success(f"Empresa **{emp.get('nombre')}** eliminada correctamente")
                                st.cache_data.clear()
                                st.cache_resource.clear()
                                import time
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                notify_error("No se pudo eliminar la empresa", {"details": str(e)})

    with tab_new:
        if empresas:
            st.warning("⚠️ Ya tienes una empresa. No puedes crear más empresas.")
            st.info("""
            Si necesitas crear una nueva empresa, crea una cuenta diferente o contacta a tu administrador.
            """)
        else:
            st.info("📋 Crea tu primera empresa para comenzar a usar el sistema.")
            with st.form("new_empresa"):
                col1, col2 = st.columns(2)
                with col1:
                    codigo = st.text_input("Código *", placeholder="EMP001")
                    nombre = st.text_input("Nombre *", placeholder="Mi Empresa S.A.")
                    ruc = st.text_input("RUC", placeholder="80012345-6")
                with col2:
                    telefono = st.text_input("Teléfono", placeholder="+595 21 123456")
                    email = st.text_input("Email", placeholder="info@miempresa.com")
                    moneda = st.selectbox("Moneda", ["PYG", "USD"])
                direccion = st.text_area("Dirección", placeholder="Calle Principal 123, Asunción")

                if st.form_submit_button("Crear Empresa", type="primary", use_container_width=True):
                    if not codigo or not nombre:
                        notify_error("El código y nombre de la empresa son obligatorios")
                    else:
                        payload = {
                            "codigo": codigo, "nombre": nombre, "ruc": ruc,
                            "telefono": telefono, "email": email,
                            "moneda_principal": moneda, "direccion": direccion,
                        }
                        result, err = api.create_empresa(payload)
                        if err:
                            notify_error("No se pudo crear la empresa", {"error": str(err), "payload": payload})
                        else:
                            notify_success(f"Empresa **{nombre}** creada correctamente. Ya puedes navegar a otras secciones.")
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            st.session_state["empresa_activa"] = result
                            import time
                            time.sleep(0.5)
                            st.rerun()
