"""Session persistence manager for Streamlit."""
import json
import os
from pathlib import Path
import streamlit as st
import api_client as api


# Directorio para guardar sesión
SESSION_DIR = Path.home() / ".facturacion_session"
SESSION_FILE = SESSION_DIR / "session.json"


def ensure_session_dir():
    """Crear directorio si no existe."""
    SESSION_DIR.mkdir(exist_ok=True, mode=0o700)  # Permisos seguros


def save_session(access_token: str, refresh_token: str, user: dict, empresa_activa: dict):
    """Guardar sesión en archivo local."""
    try:
        ensure_session_dir()
        session_data = {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": user,
            "empresa_activa": empresa_activa,
        }
        with open(SESSION_FILE, "w") as f:
            json.dump(session_data, f, indent=2)
        # Establecer permisos seguros
        os.chmod(SESSION_FILE, 0o600)
    except Exception as e:
        print(f"Error guardando sesión: {e}")


def load_session():
    """Cargar sesión guardada desde archivo."""
    try:
        if SESSION_FILE.exists():
            with open(SESSION_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error cargando sesión: {e}")
    return None


def verify_and_restore_session():
    """
    Verificar si hay una sesión guardada y restaurarla si los tokens son válidos.
    Devuelve True si la sesión fue restaurada, False si no.
    """
    # Si ya hay sesión activa, no hacer nada
    if st.session_state.get("access_token"):
        return True
    
    # Intentar cargar sesión guardada
    saved_session = load_session()
    if not saved_session:
        return False
    
    access_token = saved_session.get("access_token")
    refresh_token = saved_session.get("refresh_token")
    
    if not access_token:
        return False
    
    # Verificar si el token todavía es válido
    try:
        # Intentar obtener el perfil con el token guardado
        st.session_state["access_token"] = access_token
        st.session_state["refresh_token"] = refresh_token
        
        perfil, err = api.get_perfil()
        
        if err:
            # Token no válido, intentar refrescar
            if refresh_token:
                new_data, refresh_err = api.refresh_token(refresh_token)
                if refresh_err:
                    # No se pudo refrescar, limpiar sesión guardada
                    clear_session()
                    return False
                else:
                    # Se refrescó correctamente
                    st.session_state["access_token"] = new_data.get("access")
                    st.session_state["refresh_token"] = new_data.get("refresh", refresh_token)
                    st.session_state["user"] = saved_session.get("user") or perfil or {}
                    st.session_state["empresa_activa"] = saved_session.get("empresa_activa")
                    
                    # Guardar sesión actualizada
                    save_session(
                        st.session_state["access_token"],
                        st.session_state["refresh_token"],
                        st.session_state["user"],
                        st.session_state["empresa_activa"],
                    )
                    return True
            else:
                # No hay refresh token, limpiar sesión
                clear_session()
                return False
        else:
            # Token válido, restaurar sesión
            st.session_state["access_token"] = access_token
            st.session_state["refresh_token"] = refresh_token
            st.session_state["user"] = saved_session.get("user") or perfil or {}
            st.session_state["empresa_activa"] = saved_session.get("empresa_activa")
            return True
    
    except Exception as e:
        print(f"Error verificando sesión: {e}")
        clear_session()
        return False


def clear_session():
    """Limpiar sesión guardada."""
    try:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
    except Exception as e:
        print(f"Error limpiando sesión: {e}")
    
    # Limpiar sesión de Streamlit
    for k in ["access_token", "refresh_token", "user", "empresa_activa"]:
        st.session_state[k] = None


def logout_and_clear():
    """Logout y limpiar sesión guardada."""
    clear_session()
