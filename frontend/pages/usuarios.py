"""Users management page for the current empresa."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results, notify_success, notify_error, show_session_notifications


def render():
    show_session_notifications()
    st.header("👥 Usuarios de la Empresa")
    
    # Get current empresa
    empresa = st.session_state.get("empresa_activa")
    if not empresa:
        st.error("No hay empresa seleccionada. Selecciona una en 🏢 Empresas")
        return
    
    user = st.session_state.get("user") or {}
    user_rol = user.get("rol", "")
    
    st.write(f"**Empresa:** {empresa.get('nombre')}")
    st.write(f"**Tu Rol:** {user_rol.title() if user_rol else 'Sin rol'}")
    
    if user_rol != "admin":
        st.warning("⚠️ Solo administradores pueden gestionar usuarios.")
        return
    
    st.divider()
    
    tab_usuarios, tab_invitar, tab_accesos = st.tabs(["📋 Usuarios Actuales", "➕ Invitar Usuario", "🔐 Configurar Accesos"])
    
    # ── Usuarios Actuales ─────────────────────────────────────────────────────
    with tab_usuarios:
        st.subheader("Usuarios en esta Empresa")
        
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("🔄 Actualizar", use_container_width=True, key="refresh_users"):
                st.rerun()
        
        # Listar membresías de la empresa
        data, err = api.list_memberships(empresa["id"])
        memberships = results(data) if data else []
        
        if err:
            notify_error(f"Error cargando usuarios: {err}")
        elif not memberships:
            st.info("📭 No se encontraron usuarios. Tu información:")
            st.write(f"- **Email:** {user.get('email', '-')}")
            st.write(f"- **Nombre:** {user.get('first_name', '')} {user.get('last_name', '')}")
            st.write(f"- **Rol:** {user_rol.title()}")
        else:
            # Mostrar tabla de usuarios
            rows = []
            for m in memberships:
                u = m.get("usuario_detail") or {}
                rows.append({
                    "Email": u.get("email", m.get("usuario_email", "-")),
                    "Nombre": u.get("first_name", "") + " " + u.get("last_name", ""),
                    "Rol": m.get("rol", "-").title(),
                    "Activo": "✅" if m.get("activo") else "❌",
                    "id": m.get("id"),
                })
            
            df = pd.DataFrame(rows)
            st.dataframe(df[["Email", "Nombre", "Rol", "Activo"]], use_container_width=True, hide_index=True)
            
            # Acciones por usuario
            for m in memberships:
                u = m.get("usuario_detail") or {}
                u_email = u.get("email", m.get("usuario_email", "-"))
                m_id = m.get("id")
                m_rol = m.get("rol", "")
                m_activo = m.get("activo", True)
                
                # No permitir cambiar el propio usuario
                if u.get("id") == user.get("id") or u_email == user.get("email"):
                    continue
                
                with st.expander(f"⚙️ {u_email} — {m_rol.title()}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        new_rol = st.selectbox(
                            "Cambiar Rol",
                            ["vendedor", "contador", "admin"],
                            index=["vendedor", "contador", "admin"].index(m_rol) if m_rol in ["vendedor", "contador", "admin"] else 0,
                            key=f"rol_{m_id}",
                            format_func=lambda x: {"admin": "👑 Admin", "vendedor": "🧑‍💼 Vendedor", "contador": "🧮 Contador"}.get(x, x)
                        )
                    with col2:
                        if st.button("💾 Guardar Rol", key=f"save_rol_{m_id}", use_container_width=True):
                            ok, err = api.update_membership(m_id, {"rol": new_rol})
                            if ok:
                                notify_success(f"Rol de {u_email} actualizado a {new_rol.title()}")
                                st.rerun()
                            else:
                                notify_error(f"Error: {err}")
                    with col3:
                        label = "❌ Desactivar" if m_activo else "✅ Activar"
                        if st.button(label, key=f"toggle_{m_id}", use_container_width=True):
                            ok, err = api.update_membership(m_id, {"activo": not m_activo})
                            if ok:
                                notify_success(f"Usuario {u_email} {'desactivado' if m_activo else 'activado'}")
                                st.rerun()
                            else:
                                notify_error(f"Error: {err}")
    
    # ── Invitar Usuario ───────────────────────────────────────────────────────
    with tab_invitar:
        st.subheader("Invitar Nuevo Usuario")
        
        col1, col2 = st.columns(2)
        with col1:
            email = st.text_input("Email del Usuario *", placeholder="usuario@example.com")
            nombre = st.text_input("Nombre", placeholder="Juan")
        with col2:
            apellido = st.text_input("Apellido", placeholder="Pérez")
            rol = st.selectbox(
                "Rol *",
                ["vendedor", "contador", "admin"],
                format_func=lambda x: {
                    "admin": "👑 Administrador",
                    "vendedor": "🧑‍💼 Vendedor",
                    "contador": "🧮 Contador",
                }.get(x, x)
            )
        
        st.caption("* Campos obligatorios")
        st.info("El usuario recibirá una invitación para unirse a la empresa. "
                "Si no tiene cuenta, se creará una con contraseña temporal.")
        
        if st.button("📨 Enviar Invitación", type="primary", use_container_width=True):
            if not email:
                st.error("El email es obligatorio.")
            else:
                result, err = api.invitar_usuario(
                    email=email,
                    rol=rol,
                    first_name=nombre,
                    last_name=apellido
                )
                if err:
                    st.error(f"Error: {err}")
                else:
                    st.success(f"✅ Invitación enviada a **{email}**")
                    st.info(f"""
                    Se ha creado/invitado el usuario:
                    - **Email:** {result.get('email')}
                    - **Nombre:** {result.get('nombre', '-')}
                    - **Rol:** {result.get('rol').title()}
                    """)
                    st.balloons()

    # ── Configurar Accesos ────────────────────────────────────────────────────
    with tab_accesos:
        st.subheader("🔐 Configurar Accesos por Rol")
        st.caption("Define qué módulos puede acceder cada rol. El Administrador siempre tiene acceso total.")

        # Obtener permisos actuales
        permisos_data, permisos_err = api.get_mis_permisos()
        if permisos_err:
            notify_error(f"Error cargando permisos: {permisos_err}")
        else:
            modulos_disponibles = permisos_data.get("modulos_disponibles", [])
            defaults = permisos_data.get("defaults", {})

            # Cargar configs existentes
            configs_data, _ = api.list_config_acceso(empresa["id"])
            configs_list = results(configs_data) if configs_data else []
            configs_by_rol = {c["rol"]: c for c in configs_list}

            for rol_key in ["contador", "vendedor"]:
                rol_label = {"contador": "🧮 Contador", "vendedor": "🧑‍💼 Vendedor"}[rol_key]
                st.write(f"### {rol_label}")

                existing = configs_by_rol.get(rol_key)
                if existing:
                    current_modulos = existing.get("modulos_permitidos", [])
                else:
                    current_modulos = defaults.get(rol_key, [])

                # Checkboxes por módulo
                selected = []
                cols = st.columns(3)
                for i, mod in enumerate(modulos_disponibles):
                    mod_key = mod["key"]
                    mod_label = mod["label"]
                    # Skip admin-only modules
                    if mod_key in ("empresas", "usuarios"):
                        continue
                    with cols[i % 3]:
                        checked = st.checkbox(
                            mod_label,
                            value=mod_key in current_modulos,
                            key=f"perm_{rol_key}_{mod_key}"
                        )
                        if checked:
                            selected.append(mod_key)

                # Always include dashboard
                if "dashboard" not in selected:
                    selected.insert(0, "dashboard")

                if st.button(f"💾 Guardar accesos de {rol_label}", key=f"save_perm_{rol_key}", use_container_width=True):
                    config_id = existing.get("id") if existing else None
                    ok, err = api.save_config_acceso(
                        config_id=config_id,
                        empresa_id=empresa["id"],
                        rol=rol_key,
                        modulos=selected
                    )
                    if ok:
                        notify_success(f"Accesos de {rol_label} guardados correctamente")
                        st.rerun()
                    else:
                        notify_error(f"Error: {err}")

                st.divider()
