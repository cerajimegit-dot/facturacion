"""Shared helpers for frontend pages."""
import streamlit as st
import time


def fmt(value, prefix=""):
    """Format a number value safely (handles strings, None, etc.)."""
    try:
        n = float(value)
        return f"{prefix}{n:,.0f}"
    except (TypeError, ValueError):
        return str(value) if value else "-"


def results(data):
    """Extract list from paginated or plain API response."""
    if data is None:
        return []
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("results", [])
    return []


def notify_success(message: str, duration: float = 2.0, auto_close=True):
    """Show success notification with auto-close. Persists through st.rerun()."""
    # Show immediately
    st.toast(f"✅ {message}", icon="✅")
    st.success(f"✅ {message}")
    
    # Also store in session state to show after rerun
    if "success_messages" not in st.session_state:
        st.session_state.success_messages = []
    st.session_state.success_messages.append(message)


def notify_error(message: str, details: dict = None, auto_close=False):
    """Show error notification with optional technical details. Persists through st.rerun()."""
    st.error(f"❌ {message}")
    if details:
        with st.expander("📋 Detalles técnicos"):
            st.json(details)
    
    # Also store in session state
    if "error_messages" not in st.session_state:
        st.session_state.error_messages = []
    st.session_state.error_messages.append((message, details))


def notify_warning(message: str):
    """Show warning notification. Persists through st.rerun()."""
    st.warning(f"⚠️ {message}")
    
    if "warning_messages" not in st.session_state:
        st.session_state.warning_messages = []
    st.session_state.warning_messages.append(message)


def notify_info(message: str):
    """Show info notification. Persists through st.rerun()."""
    st.info(f"ℹ️ {message}")
    
    if "info_messages" not in st.session_state:
        st.session_state.info_messages = []
    st.session_state.info_messages.append(message)


def show_session_notifications():
    """Show any notifications stored in session state and clear them."""
    # Show success messages
    if st.session_state.get("success_messages"):
        for msg in st.session_state.success_messages:
            st.toast(f"✅ {msg}", icon="✅")
            st.success(f"✅ {msg}")
        st.session_state.success_messages = []
    
    # Show error messages
    if st.session_state.get("error_messages"):
        for msg, details in st.session_state.error_messages:
            st.error(f"❌ {msg}")
            if details:
                with st.expander("📋 Detalles técnicos"):
                    st.json(details)
        st.session_state.error_messages = []
    
    # Show warning messages
    if st.session_state.get("warning_messages"):
        for msg in st.session_state.warning_messages:
            st.warning(f"⚠️ {msg}")
        st.session_state.warning_messages = []
    
    # Show info messages
    if st.session_state.get("info_messages"):
        for msg in st.session_state.info_messages:
            st.info(f"ℹ️ {msg}")
        st.session_state.info_messages = []
