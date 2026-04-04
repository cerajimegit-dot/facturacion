"""Login & Registration page."""
import streamlit as st
import api_client as api


def render():
    st.markdown(
        "<h1 style='text-align:center;'>📊 Sistema de Facturación</h1>"
        "<p style='text-align:center;color:gray;'>Multi-Empresa</p>",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        tab_login, tab_registro = st.tabs(["🔐 Iniciar Sesión", "📝 Registrarse"])

        with tab_login:
            with st.form("login_form"):
                email = st.text_input("Email", placeholder="admin@example.com")
                password = st.text_input("Contraseña", type="password")
                submitted = st.form_submit_button("Ingresar", use_container_width=True, type="primary")

                if submitted:
                    if not email or not password:
                        st.error("Completa todos los campos.")
                    else:
                        data, err = api.login(email, password)
                        if err:
                            st.error(f"Error de autenticación: {err}")
                        else:
                            st.session_state["access_token"] = data.get("access")
                            st.session_state["refresh_token"] = data.get("refresh")
                            # Use user data from login response or fetch profile
                            user_data = data.get("user")
                            if user_data:
                                st.session_state["user"] = user_data
                            else:
                                perfil, _ = api.get_perfil()
                                st.session_state["user"] = perfil or {"email": email}
                            
                            # Store empresa data if available
                            empresa_data = data.get("empresa")
                            if empresa_data:
                                st.session_state["empresa_activa"] = empresa_data
                                # Mostrar logo
                                logo_url = empresa_data.get("logo_url")
                                if logo_url:
                                    st.image(logo_url, width=200)
                            
                            st.success("¡Bienvenido!")
                            st.rerun()

        with tab_registro:
            with st.form("register_form"):
                st.subheader("📝 Información de Usuario")
                col1, col2 = st.columns(2)
                with col1:
                    r_nombre = st.text_input("Nombre *", placeholder="Juan")
                    r_email = st.text_input("Email *", placeholder="usuario@example.com")
                with col2:
                    r_apellido = st.text_input("Apellido *", placeholder="Pérez")
                    r_pass = st.text_input("Contraseña *", type="password", key="reg_pass")
                r_pass2 = st.text_input("Confirmar Contraseña *", type="password", key="reg_pass2")
                
                st.divider()
                st.subheader("🏢 Crear Empresa (Opcional)")
                create_empresa = st.checkbox("Crear nueva empresa al registrarse")
                
                if create_empresa:
                    col1, col2 = st.columns(2)
                    with col1:
                        emp_codigo = st.text_input("Código Empresa", placeholder="EMP001")
                    with col2:
                        emp_nombre = st.text_input("Nombre Empresa", placeholder="Mi Empresa S.A.")
                else:
                    emp_codigo = ""
                    emp_nombre = ""
                
                r_submit = st.form_submit_button("Crear Cuenta", use_container_width=True, type="primary")

                if r_submit:
                    if not all([r_nombre, r_apellido, r_email, r_pass]):
                        st.error("Completa todos los campos obligatorios.")
                    elif r_pass != r_pass2:
                        st.error("Las contraseñas no coinciden.")
                    elif create_empresa and not all([emp_codigo, emp_nombre]):
                        st.error("Completa código y nombre de empresa.")
                    else:
                        reg_data = {
                            "email": r_email,
                            "password": r_pass,
                            "password2": r_pass2,
                            "first_name": r_nombre,
                            "last_name": r_apellido,
                        }
                        if create_empresa:
                            reg_data["empresa_codigo"] = emp_codigo
                            reg_data["empresa_nombre"] = emp_nombre
                        
                        data, err = api.register_full(reg_data)
                        if err:
                            st.error(f"Error: {err}")
                        else:
                            st.success("✅ Cuenta creada. Ahora inicia sesión.")
