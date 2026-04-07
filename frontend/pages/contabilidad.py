"""Página de Contabilidad - Plan de Cuentas y Asientos."""
import streamlit as st
import pandas as pd
import api_client as api
import datetime
from helpers import results, fmt, notify_success, notify_error, show_session_notifications


def render():
    """Renderizar página de contabilidad."""
    show_session_notifications()
    st.title("📊 Contabilidad")
    
    # Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Plan de Cuentas",
        "➕ Nueva Cuenta",
        "📤 Importar Excel",
        "Asientos",
        "Cotizaciones"
    ])
    
    empresa_id = st.session_state.get("empresa_activa", {}).get("id")
    
    with tab1:
        render_plan_cuentas(empresa_id)
    
    with tab2:
        render_crear_cuenta(empresa_id)
    
    with tab3:
        render_importar_excel(empresa_id)
    
    with tab4:
        render_asientos(empresa_id)
    
    with tab5:
        render_cotizaciones(empresa_id)


def render_plan_cuentas(empresa_id):
    """Renderer para Plan de Cuentas."""
    show_session_notifications()
    st.header("Plan de Cuentas")
    
    # Opciones de filtro
    col1, col2, col3 = st.columns(3)
    
    with col1:
        condicion = st.selectbox(
            "Filtrar por condición",
            ["Todos", "deudora", "acreedora"],
            key="plan_condicion"
        )
    
    with col2:
        clase = st.selectbox(
            "Filtrar por clase",
            ["Todos", "sintetica", "analitica"],
            key="plan_clase"
        )
    
    with col3:
        search = st.text_input("Buscar código o descripción", key="plan_search")
    
    # Obtener datos
    try:
        cond_param = condicion if condicion != "Todos" else ""
        data, err = api.list_plan_cuentas(condicion=cond_param, search=search)
        
        if err:
            notify_error("Error cargando cuentas contables", {"details": str(err)})
        else:
            cuentas = results(data)
            
            # Aplicar filtros adicionales en client side
            if clase != "Todos":
                cuentas = [c for c in cuentas if c.get("clase") == clase]
            
            # Mostrar tabla
            if cuentas:
                st.success(f"✅ {len(cuentas)} cuentas encontradas")
                
                df = pd.DataFrame([
                    {
                        "Código": c.get("codigo_cuenta"),
                        "Descripción": c.get("descripcion"),
                        "Condición": c.get("condicion"),
                        "Clase": c.get("clase"),
                        "Ítem": "✓" if c.get("acepta_item") else "✗",
                        "CC": "✓" if c.get("acepta_centro_costo") else "✗",
                        "Nivel": "✓" if c.get("acepta_nivel") else "✗",
                    }
                    for c in cuentas
                ])
                
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No hay cuentas disponibles con los filtros seleccionados")
    
    except Exception as e:
        notify_error(f"Error procesando plan de cuentas", {"details": str(e)})


def render_crear_cuenta(empresa_id):
    """Formulario para crear una nueva cuenta contable."""
    show_session_notifications()
    st.header("Crear Nueva Cuenta Contable")
    
    with st.form("crear_cuenta"):
        col1, col2 = st.columns(2)
        
        with col1:
            codigo = st.text_input("Código de Cuenta *", placeholder="Ej: 2110", key="cuenta_codigo")
            condicion = st.selectbox("Condición *", ["deudora", "acreedora"], key="cuenta_condicion")
            acepta_item = st.checkbox("Acepta Ítem", value=False)
        
        with col2:
            descripcion = st.text_input("Descripción *", placeholder="Descripción de la cuenta", key="cuenta_desc")
            clase = st.selectbox("Clase *", ["sintetica", "analitica"], key="cuenta_clase")
            acepta_cc = st.checkbox("Acepta Centro de Costo", value=False)
        
        acepta_nivel = st.checkbox("Acepta Nivel", value=False)
        
        if st.form_submit_button("💾 Crear Cuenta", type="primary", use_container_width=True):
            if not codigo or not descripcion:
                notify_error("Código y Descripción son obligatorios")
            else:
                payload = {
                    'codigo_cuenta': codigo,
                    'descripcion': descripcion,
                    'condicion': condicion,
                    'clase': clase,
                    'acepta_item': acepta_item,
                    'acepta_centro_costo': acepta_cc,
                    'acepta_nivel': acepta_nivel,
                    'activa': True
                }
                
                result, err = api.create_plan_cuentas(payload)
                if err:
                    notify_error("No se pudo crear la cuenta", {"details": str(err)})
                else:
                    notify_success(f"✅ Cuenta {codigo} - {descripcion} creada exitosamente")
                    st.rerun()


def render_importar_excel(empresa_id):
    """Importar cuentas contables desde Excel (formato ANEXO 1)."""
    show_session_notifications()
    st.header("Importar Plan de Cuentas desde Excel")
    
    st.info(
        "Sube un archivo Excel con el formato **ANEXO 1 (Balance General SET/DNIT)**.\n\n"
        "El sistema espera:\n"
        "- **Columna A**: Código de cuenta (ej: 1, 1.01, 1.01.01)\n"
        "- **Columna B**: Descripción de la cuenta\n"
        "- Las filas con 'xx' (placeholders) se ignoran automáticamente"
    )
    
    uploaded_file = st.file_uploader(
        "Seleccionar archivo Excel",
        type=["xlsx", "xls"],
        key="import_excel_file"
    )
    
    if uploaded_file:
        st.write(f"📄 Archivo: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("👁️ Vista Previa", use_container_width=True):
                file_bytes = uploaded_file.getvalue()
                data, err = api.import_plan_cuentas(file_bytes, uploaded_file.name, preview=True)
                if err:
                    notify_error("Error al previsualizar", {"details": str(err)})
                else:
                    st.session_state["import_preview"] = data
        
        with col2:
            if st.button("📥 Importar Ahora", type="primary", use_container_width=True):
                file_bytes = uploaded_file.getvalue()
                data, err = api.import_plan_cuentas(file_bytes, uploaded_file.name, preview=False)
                if err:
                    notify_error("Error al importar", {"details": str(err)})
                else:
                    st.session_state.pop("import_preview", None)
                    notify_success(
                        f"✅ Importación completada: "
                        f"{data.get('creadas', 0)} creadas, "
                        f"{data.get('actualizadas', 0)} actualizadas, "
                        f"{data.get('parentescos', 0)} parentescos. "
                        f"Total en BD: {data.get('total_en_bd', 0)}"
                    )
                    st.rerun()
        
        # Show preview if available
        preview = st.session_state.get("import_preview")
        if preview:
            st.divider()
            st.subheader("Vista Previa")
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Total cuentas", preview.get("total", 0))
            col_b.metric("Nuevas", preview.get("nuevas", 0))
            col_c.metric("Ya existentes", preview.get("existentes", 0))
            
            cuentas_preview = preview.get("cuentas", [])
            if cuentas_preview:
                df_preview = pd.DataFrame([
                    {
                        "Código": c.get("codigo_cuenta"),
                        "Descripción": c.get("descripcion"),
                        "Estado": "✅ Ya existe" if c.get("existe") else "🆕 Nueva",
                    }
                    for c in cuentas_preview
                ])
                st.dataframe(df_preview, use_container_width=True, hide_index=True)


def render_asientos(empresa_id):
    """Renderer para Asientos Contables."""
    show_session_notifications()
    st.header("Asientos Contables")
    
    col1, col2 = st.columns(2)
    
    with col1:
        estado = st.selectbox(
            "Filtrar por estado",
            ["Todos", "borrador", "registrado", "reversado"],
            key="asiento_estado"
        )
    
    with col2:
        search = st.text_input("Buscar número de asiento", placeholder="ASI-001...", key="asiento_search")
    
    # Obtener datos
    try:
        estado_param = estado if estado != "Todos" else ""
        data, err = api.list_asientos(estado=estado_param, search=search)
        
        if err:
            notify_error("Error cargando asientos", {"details": str(err)})
        else:
            asientos = results(data)
            
            if asientos:
                st.success(f"✅ {len(asientos)} asientos encontrados")
                
                df = pd.DataFrame([
                    {
                        "Número": a.get("numero_asiento"),
                        "Factura": a.get("compra_numero", "-"),
                        "Fecha": a.get("fecha"),
                        "Tipo": a.get("tipo_asiento", "general"),
                        "Estado": a.get("estado"),
                        "Debe": f"{float(a.get('total_debe', 0)):,.0f}",
                        "Haber": f"{float(a.get('total_haber', 0)):,.0f}",
                    }
                    for a in asientos
                ])
                
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Detalle expandible de cada asiento
                for a in asientos:
                    factura = a.get("compra_numero", "")
                    label = f"📄 Asiento {a.get('numero_asiento')}"
                    if factura:
                        label += f" — Factura: {factura}"
                    with st.expander(label):
                        detail, err_d = api.get_asiento(a["id"])
                        if err_d:
                            st.error(f"Error cargando detalle: {err_d}")
                        elif detail:
                            st.write(f"**Descripción:** {detail.get('descripcion', '-')}")
                            if detail.get("compra_numero"):
                                st.write(f"**Nro. Factura:** {detail.get('compra_numero')}")
                            if detail.get("proveedor_nombre"):
                                st.write(f"**Proveedor:** {detail.get('proveedor_nombre')}")
                            lineas = detail.get("lineas", [])
                            if lineas:
                                df_lineas = pd.DataFrame([
                                    {
                                        "Cuenta": l.get("cuenta_descripcion", ""),
                                        "Observación": l.get("observacion", ""),
                                        "Debe": fmt(float(l.get("debe", 0)), "₲") if float(l.get("debe", 0)) > 0 else "",
                                        "Haber": fmt(float(l.get("haber", 0)), "₲") if float(l.get("haber", 0)) > 0 else "",
                                    }
                                    for l in lineas
                                ])
                                st.dataframe(df_lineas, use_container_width=True, hide_index=True)
            else:
                st.info("No hay asientos registrados. Los asientos se generan automáticamente al **recibir** una compra (estado → recepcionada).")
    
    except Exception as e:
        notify_error(f"Error procesando asientos", {"details": str(e)})


def render_reportes(empresa_id):
    """Renderer para Reportes Contables."""
    show_session_notifications()
    st.header("Reportes Contables")
    
    reporte_type = st.selectbox(
        "Selecciona tipo de reporte",
        ["Balance General", "Libro Mayor", "Libro Diario"],
        key="reporte_type"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        desde = st.date_input("Desde", key="reporte_desde")
    with col2:
        hasta = st.date_input("Hasta", key="reporte_hasta")
    
    if st.button("📊 Generar Reporte"):
        try:
            # Mapear tipos de reporte
            tipo_map = {
                "Balance General": "balance",
                "Libro Mayor": "mayor",
                "Libro Diario": "diario"
            }
            
            tipo = tipo_map.get(reporte_type, "balance")
            
            st.info(f"Generando {reporte_type} desde {desde} hasta {hasta}...")
            
            # Aquí iría la llamada al API para generar el reporte
            notify_success(f"Reporte generado exitosamente")
            
            # Mostrar datos de ejemplo
            st.write("📋 Vista previa del reporte:")
            example_data = {
                "Código": ["1100", "2100", "3100"],
                "Descripción": ["Activos Corrientes", "Pasivos Corrientes", "Patrimonio"],
                "Debe": [1000000, 500000, 0],
                "Haber": [0, 0, 1500000],
                "Saldo": [1000000, -500000, -1500000]
            }
            st.dataframe(example_data)
        
        except Exception as e:
            notify_error(f"Error generando reporte", {"details": str(e)})


def render_cotizaciones(empresa_id):
    """Renderer para Cotizaciones Diarias."""
    show_session_notifications()
    st.header("Cotizaciones Diarias")

    # ── Formulario para cargar nueva cotización ───────────────────────────
    with st.expander("➕ Cargar Nueva Cotización", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            cot_fecha = st.date_input("Fecha", value=datetime.date.today(), key="cot_nueva_fecha")
        with col2:
            cot_moneda = st.selectbox("Moneda Origen", ["USD", "EUR", "ARS", "BRL"], key="cot_nueva_moneda")
        with col3:
            cot_tasa = st.number_input("Tasa (ej: 7500 para 1 USD = 7500 PYG)", min_value=0.01, step=100.0, format="%.2f", key="cot_nueva_tasa")

        if st.button("💾 Guardar Cotización", type="primary", use_container_width=True, key="btn_guardar_cot"):
            if cot_tasa <= 0:
                notify_error("La tasa debe ser mayor a 0")
            else:
                payload = {
                    "fecha": cot_fecha.isoformat(),
                    "moneda_origen": cot_moneda,
                    "moneda_destino": "PYG",
                    "tasa": str(cot_tasa),
                }
                result, err = api.create_cotizacion_diaria(payload)
                if err:
                    notify_error(f"Error al guardar cotización: {err}")
                else:
                    notify_success(f"✅ Cotización {cot_moneda}/PYG = {cot_tasa:,.2f} guardada para {cot_fecha}")
                    st.rerun()

    st.divider()

    # ── Listado de cotizaciones ───────────────────────────────────────────
    col1, col2 = st.columns(2)
    
    with col1:
        moneda_origen = st.selectbox(
            "Filtrar por moneda",
            ["Todas", "USD", "EUR", "ARS", "BRL"],
            key="cotizacion_origen"
        )
    
    with col2:
        search = st.text_input("Buscar...", key="cotizacion_search")
    
    try:
        # Obtener cotizaciones
        moneda_param = moneda_origen if moneda_origen != "Todas" else ""
        data, err = api.list_cotizaciones_diarias(moneda=moneda_param, search=search)
        
        if err:
            notify_error("Error cargando cotizaciones", {"details": str(err)})
        else:
            cotizaciones = results(data)
            
            if cotizaciones:
                st.success(f"✅ {len(cotizaciones)} cotizaciones disponibles")
                
                df = pd.DataFrame([
                    {
                        "Fecha": c.get("fecha"),
                        "Origen": c.get("moneda_origen"),
                        "Destino": c.get("moneda_destino"),
                        "Tasa": f"{float(c.get('tasa', 0)):,.2f}",
                    }
                    for c in cotizaciones
                ])
                
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("No hay cotizaciones cargadas. Use el formulario de arriba para agregar la primera.")
    
    except Exception as e:
        notify_error(f"Error procesando cotizaciones", {"details": str(e)})
