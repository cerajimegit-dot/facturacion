"""Users management page for the current empresa."""
import streamlit as st
import pandas as pd
import api_client as api
from helpers import results


def render():
    st.header("👥 Usuarios de la Empresa")
    
    # Get current empresa
    empresa = st.session_state.get("empresa_activa")
    if not empresa:
        st.error("No hay empresa seleccionada. Selecciona una en 🏢 Empresas")
        return
    
    user = st.session_state.get("user", {})
    user_rol = user.get("rol", "")
    
    st.write(f"**Empresa:** {empresa.get('nombre')}")
    st.write(f"**Tu Rol:** {user_rol.title()}")
    
    if user_rol != "admin":
        st.warning("⚠️ Solo administradores pueden gestionar usuarios.")
        return
    
    st.divider()
    
    tab_usuarios, tab_invitar = st.tabs(["📋 Usuarios Actuales", "➕ Invitar Usuario"])
    
    # ── Usuarios Actuales ─────────────────────────────────────────────────────
    with tab_usuarios:
        st.subheader("Usuarios en esta Empresa")
        
        # Para ahora, mostrar información del usuario actual
        # En una aplicación real, hay que crear un endpoint para listar usuarios
        st.info("""
        Los usuarios de tu empresa se mostrarán aquí.
        
        **Tu información:**
        - Email: {}
        - Nombre: {}
        - Rol: {}
        """.format(
            user.get("email", "-"),
            user.get("first_name", "") + " " + user.get("last_name", ""),
            user_rol.title()
        ))
    
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
