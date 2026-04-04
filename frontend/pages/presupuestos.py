"""Presupuestos page for Streamlit frontend."""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import api_client as api
from helpers import results, notify_success, notify_error, notify_info, show_session_notifications


API_BASE = "http://localhost:8000/api/v1"


def get_clientes():
    """Fetch list of clientes from API."""
    data, err = api.list_clientes()
    if err:
        notify_error("No se pudieron cargar los clientes", {"details": str(err)})
        return []
    return results(data) if data else []


def get_productos():
    """Fetch list of productos from API."""
    # Clear cache to ensure fresh data from product updates
    st.cache_data.clear()
    
    data, err = api.list_productos()
    if err:
        notify_error("No se pudieron cargar los productos", {"details": str(err)})
        return []
    return results(data) if data else []


def get_presupuestos():
    """Fetch list of presupuestos from API."""
    data, err = api.list_presupuestos()
    if err:
        notify_error("No se pudieron cargar los presupuestos", {"details": str(err)})
        return []
    return results(data) if data else []


def create_presupuesto(cliente_id, detalles, condiciones_pago=""):
    """Create a new presupuesto."""
    payload = {
        "cliente": cliente_id,
        "detalles": detalles,
        "condiciones_pago": condiciones_pago,
        "fecha_vigencia": (datetime.now() + timedelta(days=30)).date().isoformat(),
    }
    
    result, err = api.create_presupuesto(payload)
    if err:
        notify_error("No se pudo crear el presupuesto", {"error": str(err), "payload": payload})
        return None
    return result


def send_presupuesto_email(presupuesto_id):
    """Send presupuesto via email."""
    result, err = api.enviar_presupuesto_email(presupuesto_id)
    if err:
        notify_error("No se pudo enviar el presupuesto por email", {"details": str(err)})
        return False
    notify_success("Presupuesto enviado por email correctamente")
    return True


def send_presupuesto_whatsapp(presupuesto_id):
    """Send presupuesto via WhatsApp."""
    result, err = api.enviar_presupuesto_whatsapp(presupuesto_id)
    if err:
        notify_error("No se pudo enviar el presupuesto por WhatsApp", {"details": str(err)})
        return False
    notify_success("Presupuesto enviado por WhatsApp correctamente")
    return True


def render():
    """Render the presupuestos page."""
    show_session_notifications()
    st.header("📋 Presupuestos")
    st.write("Crea y administra presupuestos para tus clientes")
    
    # Create two tabs
    tab1, tab2 = st.tabs(["Crear Presupuesto", "Ver Presupuestos"])
    
    with tab1:
        st.subheader("Crear Nuevo Presupuesto")
        
        col1, col2 = st.columns(2)
        
        with col1:
            clientes = get_clientes()
            if not clientes:
                st.warning("No hay clientes disponibles. Crea uno en Clientes primero.")
                return
                
            cliente_options = {c["nombre"]: c["id"] for c in clientes}
            selected_cliente = st.selectbox(
                "Selecciona Cliente",
                options=cliente_options.keys(),
                key="cliente_select"
            )
            cliente_id = cliente_options.get(selected_cliente)
        
        with col2:
            st.date_input(
                "Válido Hasta",
                value=datetime.now() + timedelta(days=30),
                key="fecha_vigencia"
            )
        
        # Condiciones de pago
        condiciones = st.text_area(
            "Condiciones de Pago",
            placeholder="Ej: Pago 50% al confirmar, 50% a la entrega",
            height=80,
            key="condiciones"
        )
        
        st.subheader("Agregar Productos/Servicios")
        
        # Initialize session state for detalles
        if "detalles_temp" not in st.session_state:
            st.session_state.detalles_temp = []
        
        # Add product form
        with st.form("add_detail_form", clear_on_submit=True):
            productos = get_productos()
            col1, col2, col3 = st.columns(3)
            
            with col1:
                use_producto = st.checkbox("Usar Producto del Catálogo")
                if use_producto and productos:
                    producto_options = {p["nombre"]: p["id"] for p in productos}
                    selected_prod = st.selectbox(
                        "Producto",
                        options=producto_options.keys(),
                        key="prod_select"
                    )
                    selected_prod_id = producto_options.get(selected_prod)
                    description = selected_prod
                else:
                    description = st.text_input("Descripción del Servicio/Producto")
                    selected_prod_id = None
            
            with col2:
                cantidad = st.number_input("Cantidad", min_value=1, value=1, step=1)
                
            with col3:
                precio = st.number_input("Precio Unitario", min_value=0.0, value=100.0, step=0.01)
            
            impuesto = st.slider("Impuesto (%)", min_value=0, max_value=100, value=19, step=1)
            
            if st.form_submit_button("➕ Agregar Línea"):
                if description or selected_prod_id:
                    detalle = {
                        "producto": selected_prod_id,
                        "descripcion": description if not use_producto else None,
                        "cantidad": cantidad,
                        "precio_unitario": precio,
                        "impuesto_porcentaje": impuesto
                    }
                    st.session_state.detalles_temp.append(detalle)
                    notify_success(f"Línea agregada: {description}")
        
        # Display current detalles
        if st.session_state.detalles_temp:
            st.subheader("Líneas del Presupuesto")
            
            data = []
            for i, det in enumerate(st.session_state.detalles_temp):
                subtotal = det["cantidad"] * det["precio_unitario"]
                impuesto_monto = subtotal * (det["impuesto_porcentaje"] / 100)
                total = subtotal + impuesto_monto
                
                data.append({
                    "Descripción": det["descripcion"] or f"Producto {det['producto']}",
                    "Cantidad": det["cantidad"],
                    "Precio Unitario": f"${det['precio_unitario']:.2f}",
                    "Subtotal": f"${subtotal:.2f}",
                    "Impuesto": f"${impuesto_monto:.2f}",
                    "Total": f"${total:.2f}"
                })
            
            df = pd.DataFrame(data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Calculate totals
            total_subtotal = sum(det["cantidad"] * det["precio_unitario"] for det in st.session_state.detalles_temp)
            total_impuesto = sum(
                (det["cantidad"] * det["precio_unitario"]) * (det["impuesto_porcentaje"] / 100)
                for det in st.session_state.detalles_temp
            )
            total_general = total_subtotal + total_impuesto
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Subtotal", f"${total_subtotal:.2f}")
            with col2:
                st.metric("Total Impuesto", f"${total_impuesto:.2f}")
            with col3:
                st.metric("Total General", f"${total_general:.2f}")
            
            # Clear and create buttons
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🗑️ Limpiar", key="clear_button"):
                    st.session_state.detalles_temp = []
                    st.rerun()
            
            with col2:
                if st.button("💾 Crear Presupuesto", key="create_button"):
                    if cliente_id and st.session_state.detalles_temp:
                        result = create_presupuesto(
                            cliente_id,
                            st.session_state.detalles_temp,
                            condiciones
                        )
                        if result:
                            st.session_state.detalles_temp = []
                            st.cache_data.clear()
                            st.cache_resource.clear()
                            import time
                            time.sleep(0.5)
                            notify_success(f"Presupuesto **{result.get('numero')}** creado correctamente")
                            st.balloons()
                            st.rerun()
    
    with tab2:
        st.subheader("Mis Presupuestos")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            estado_filter = st.selectbox(
                "Filtrar por Estado",
                options=["Todos", "Borrador", "Enviado", "Aceptado", "Rechazado", "Vencido", "Cancelado"],
                key="estado_filter"
            )
        
        with col2:
            clientes = get_clientes()
            cliente_names = ["Todos"] + [c["nombre"] for c in clientes]
            cliente_filter = st.selectbox(
                "Filtrar por Cliente",
                options=cliente_names,
                key="cliente_filter"
            )
        
        with col3:
            if st.button("🔄 Actualizar"):
                st.rerun()
        
        # Get presupuestos
        presupuestos = get_presupuestos()
        
        # Apply filters
        if estado_filter != "Todos":
            presupuestos = [p for p in presupuestos if p["estado"].lower() == estado_filter.lower()]
        
        if cliente_filter != "Todos":
            presupuestos = [p for p in presupuestos if p["cliente_nombre"] == cliente_filter]
        
        if presupuestos:
            for presupuesto in presupuestos:
                with st.expander(
                    f"Presupuesto #{presupuesto['numero']} - {presupuesto['cliente_nombre']} (${presupuesto['total']:.2f})"
                ):
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric("Estado", presupuesto["estado"].title())
                    
                    with col2:
                        st.metric("Fecha Vigencia", presupuesto["fecha_vigencia"])
                    
                    with col3:
                        st.metric("Subtotal", f"${presupuesto['subtotal']:.2f}")
                    
                    with col4:
                        st.metric("Total", f"${presupuesto['total']:.2f}")
                    
                    st.write("**Detalles:**")
                    
                    detail_data = []
                    for det in presupuesto.get("detalles", []):
                        detail_data.append({
                            "Descripción": det["descripcion"] or det.get("producto_nombre", "Sin descripción"),
                            "Cantidad": det["cantidad"],
                            "Precio Unitario": f"${det['precio_unitario']:.2f}",
                            "Total": f"${det['total']:.2f}"
                        })
                    
                    if detail_data:
                        df = pd.DataFrame(detail_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
                    
                    st.write("**Acciones:**")
                    
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if st.button(
                            "📧 Enviar Email",
                            key=f"email_{presupuesto['id']}"
                        ):
                            if send_presupuesto_email(presupuesto["id"]):
                                st.rerun()
                    
                    with col2:
                        if st.button(
                            "💬 Enviar WhatsApp",
                            key=f"whatsapp_{presupuesto['id']}"
                        ):
                            if send_presupuesto_whatsapp(presupuesto["id"]):
                                st.rerun()
                    
                    with col3:
                        if st.button(
                            "📄 Descargar PDF",
                            key=f"pdf_{presupuesto['id']}"
                        ):
                            st.info("Función PDF en desarrollo")
        else:
            st.info("No hay presupuestos disponibles")
