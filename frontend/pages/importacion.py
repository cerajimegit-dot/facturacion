"""Excel import management page."""
import streamlit as st
import pandas as pd
import io
import json
import api_client as api
from helpers import results, notify_success, notify_error, notify_info, show_session_notifications


def render():
    show_session_notifications()
    st.header("📥 Importacion desde Excel")

    # Check if empresa is active
    empresa = st.session_state.get("empresa_activa")
    if not empresa:
        st.warning("⚠️ Debes seleccionar una empresa activa antes de importar datos.")
        st.info("Ve a la sección **🏢 Empresas** para seleccionar o crear una empresa.")
        return

    tab_upload, tab_jobs = st.tabs(["📤 Subir Archivo", "📋 Trabajos de Importacion"])

    # ── Upload ────────────────────────────────────────────────────────────────
    with tab_upload:
        st.info("✅ **La empresa se usa automáticamente** de tu selección actual. No necesitas incluir empresa_codigo en el archivo Excel.")
        
        with st.expander("📖 **Guía de Plantillas por Tipo de Importación**", expanded=False):
            st.markdown("""
#### 📌 Clientes
| Columna | Obligatoria | Descripción |
|---------|:-----------:|-------------|
| `nombre` | ✅ | Razón social o nombre del cliente |
| `ruc` | ✅ | RUC / Cédula del cliente |
| `telefono` | | Teléfono de contacto |
| `email` | | Correo electrónico |
| `direccion_facturacion` | | Dirección para facturación |
| `direccion_entrega` | | Dirección de entrega |
| `tipo_cliente` | | persona_fisica / persona_juridica |
| `sector` | | Sector comercial |
| `zona` | | Zona geográfica |
| `observaciones` | | Notas adicionales |

#### 📌 Productos
| Columna | Obligatoria | Descripción |
|---------|:-----------:|-------------|
| `sku` | ✅ | Código único del producto |
| `nombre` | ✅ | Nombre del producto |
| `precio_unitario` | ✅ | Precio de venta unitario |
| `descripcion` | | Descripción del producto |
| `categoria` | | Categoría del producto |
| `variante` | | Variante (talle, color, etc.) |
| `costo` | | Costo unitario |
| `imagen_url` | | URL de la imagen |

#### 📌 Stock
| Columna | Obligatoria | Descripción |
|---------|:-----------:|-------------|
| `sku` | ✅ | Código del producto |
| `almacen_codigo` | ✅ | Código del almacén |
| `cantidad` | ✅ | Cantidad en stock |
| `ubicacion` | | Ubicación dentro del almacén |

#### 📌 Ventas
| Columna | Obligatoria | Descripción |
|---------|:-----------:|-------------|
| `numero` | ✅ | Número de factura (001-001-0000001) |
| `fecha` | ✅ | Fecha de la venta |
| `cliente_ruc` | ✅ | RUC del cliente (se auto-crea si no existe) |
| `descripcion` | ✅ | Descripción de la línea |
| `cantidad` | ✅ | Cantidad vendida |
| `precio_unitario` | ✅ | Precio unitario |
| `condicion_iva` | | gravada_10 / gravada_5 / exenta (default: gravada_10) |
| `cliente_nombre` | | Nombre (para auto-crear cliente) |
| `cliente_telefono` | | Teléfono |
| `cliente_email` | | Email |
| `moneda` | | PYG / USD (default: PYG) |
| `cotizacion_usd` | | Cotización si moneda=USD |
| `estado` | | confirmada / pagada (default: confirmada) |
| `metodo_pago` | | efectivo / transferencia / cheque / tarjeta (si estado=pagada) |
| `referencia_pago` | | Nro. de comprobante del pago |
| `notas` | | Notas de la venta |

> 💡 Se generan asientos contables automáticamente. Si `estado=pagada`, también se registra el cobro.

#### 📌 Compras
| Columna | Obligatoria | Descripción |
|---------|:-----------:|-------------|
| `numero` | ✅ | Número de factura de compra |
| `fecha` | ✅ | Fecha de la compra |
| `proveedor_ruc` | ✅ | RUC del proveedor (se auto-crea si no existe) |
| `descripcion` | ✅ | Descripción del ítem |
| `cantidad` | ✅ | Cantidad |
| `precio_unitario` | ✅ | Precio unitario |
| `condicion_iva` | | gravada_10 / gravada_5 / exenta (default: gravada_10) |
| `proveedor_nombre` | | Nombre del proveedor (para auto-crear) |
| `proveedor_pais` | | País del proveedor (default: Paraguay) |
| `proveedor_telefono` | | Teléfono del proveedor |
| `proveedor_email` | | Email del proveedor |
| `almacen_codigo` | | Código de almacén (default: ALM01, se auto-crea) |
| `sku` | | SKU del producto (si existe) |
| `moneda` | | PYG / USD (default: PYG) |
| `cotizacion_usd` | | Cotización si moneda=USD |
| `notas` | | Notas de la compra |

> 💡 La compra se marca como recepcionada y genera asiento contable automáticamente.

#### 📌 Activos Fijos
| Columna | Obligatoria | Descripción |
|---------|:-----------:|-------------|
| `codigo` | ✅ | Código único del activo |
| `nombre` | ✅ | Nombre descriptivo |
| `tipo` | ✅ | it / planta / mobiliario / vehiculo / edificio / terreno / otro |
| `valor_adquisicion` | ✅ | Monto de adquisición |
| `vida_util_anios` | ✅ | Vida útil en años |
| `fecha_adquisicion` | ✅ | Fecha de adquisición |
| `valor_residual` | | Valor residual (default: 0) |
| `descripcion` | | Descripción detallada |
| `numero_serie` | | Número de serie |
| `numero_factura` | | Nro. de factura de compra |
| `moneda` | | PYG / USD (default: PYG) |
| `clasificacion` | | Nombre de clasificación (se auto-crea) |
| `ubicacion_planta` | | Planta (se auto-crea ubicación) |
| `ubicacion_edificio` | | Edificio |
| `ubicacion_area` | | Área |
| `centro_costo_codigo` | | Código centro de costo (se auto-crea) |
| `centro_costo_descripcion` | | Descripción del centro de costo |
| `propiedad_terceros` | | SI / NO (default: NO) |

> 💡 Clasificaciones, ubicaciones y centros de costo se crean automáticamente si no existen.

#### 📌 Mixto
Archivo Excel con múltiples hojas. Cada hoja debe llamarse como el tipo: `clientes`, `productos`, `stock`, `ventas`, `compras`, `activos_fijos`.
            """)

        st.divider()

        tipo = st.selectbox("Tipo de Importacion", ["clientes", "productos", "stock", "ventas", "compras", "activos_fijos", "mixto"])
        archivo = st.file_uploader("Archivo Excel (.xlsx)", type=["xlsx", "xls"],
                                    help="Maximo 50 MB")

        if archivo:
            st.info(f"📄 **{archivo.name}** — {archivo.size / 1024:.1f} KB")

            # Store file bytes in session state for reuse
            if archivo.name not in st.session_state or st.session_state[archivo.name] != archivo.size:
                st.session_state[archivo.name] = archivo.getvalue()
                st.session_state[f"{archivo.name}_size"] = archivo.size

            file_bytes = st.session_state[archivo.name]

            # Preview
            try:
                if tipo == "mixto":
                    xls = pd.ExcelFile(io.BytesIO(file_bytes))
                    for sheet in xls.sheet_names:
                        with st.expander(f"Hoja: {sheet}"):
                            df = pd.read_excel(xls, sheet_name=sheet, nrows=10)
                            st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    df = pd.read_excel(io.BytesIO(file_bytes), nrows=10)
                    st.write("**Vista previa (10 filas):**")
                    st.dataframe(df, use_container_width=True, hide_index=True)
            except Exception as e:
                st.warning(f"No se pudo previsualizar: {e}")

            if st.button("🚀 Subir e Importar", type="primary", use_container_width=True):
                with st.spinner("Subiendo archivo y creando trabajo de importación..."):
                    # Create a file-like object from bytes for upload
                    file_obj = io.BytesIO(file_bytes)
                    file_obj.filename = archivo.name  # Set filename attribute
                    result, err = api.upload_import(file_obj, tipo)

                if err:
                    notify_error("Error al subir el archivo", {"details": str(err)})
                    st.write(f"**Detalle del error:** {err}")
                    if "No tiene acceso" in str(err):
                        st.warning("💡 **Solución:** Asegúrate de tener una empresa activa seleccionada en la sección '🏶 Empresas'.")
                    elif "archivo" in str(err).lower():
                        st.warning("💡 **Solución:** Verifica que el archivo sea un Excel válido (.xlsx o .xls) y no exceda 50 MB.")
                    elif "tipo" in str(err).lower():
                        st.warning("💡 **Solución:** Selecciona un tipo de importación válido.")
                else:
                    job_id = result.get("id")
                    notify_success(f"Archivo subido exitosamente")
                    st.info(f"📋 **Trabajo de importación creado:** `{job_id}`")

                    # PASO 1: Validar automáticamente después del upload
                    with st.spinner("🔍 Validando datos..."):
                        validate_result, validate_err = api.validar_import(job_id)
                    
                    if validate_err:
                        notify_error("Error en validación", {"details": str(validate_err)})
                    else:
                        notify_success("Validación completada exitosamente")
                        
                        # PASO 2: Verificar el estado después de validación
                        import time
                        time.sleep(1)  # Pequeña pausa para asegurar que se procesó
                        
                        job_data, job_err = api.get_import_job(job_id)
                        if not job_err and job_data:
                            job = results(job_data) if isinstance(job_data, dict) and 'results' in job_data else job_data
                            
                            filas_validas = job.get("filas_validas", 0)
                            filas_errores = job.get("filas_errores", 0)
                            
                            st.subheader("📊 Resultados de Validación")
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Filas Válidas", filas_validas)
                            with col2:
                                st.metric("Filas con Errores", filas_errores)
                            with col3:
                                st.metric("Estado", job.get("estado", "-").title())
                            
                            if filas_errores > 0:
                                st.warning(f"⚠️ Se encontraron {filas_errores} filas con errores")
                                if job.get("reporte_errores"):
                                    st.download_button(
                                        "📄 Descargar Reporte de Errores",
                                        job["reporte_errores"],
                                        f"errores_import_{job_id}.txt",
                                        "text/plain",
                                        key=f"download_errors_{job_id}"
                                    )
                            
                            if filas_validas > 0:
                                st.divider()
                                st.subheader("📥 Confirmando Importación")
                                st.info(f"📍 Se van a importar **{filas_validas}** filas...")
                                
                                # PASO 3: Confirmar/Importar automáticamente
                                with st.spinner("📥 Importando datos..."):
                                    confirm_result, confirm_err = api.confirmar_import(job_id)
                                
                                if confirm_err:
                                    notify_error("Error en importación", {"details": str(confirm_err)})
                                else:
                                    notify_success("¡Importación completada exitosamente!")
                                    
                                    # Mostrar resultado final
                                    time.sleep(1)
                                    final_job, final_err = api.get_import_job(job_id)
                                    if not final_err and final_job:
                                        final_job = results(final_job) if isinstance(final_job, dict) and 'results' in final_job else final_job
                                        st.subheader("🎉 Resumen Final")
                                        col1, col2, col3 = st.columns(3)
                                        with col1:
                                            st.metric("Filas Importadas", final_job.get("filas_importadas", 0))
                                        with col2:
                                            st.metric("Errores", final_job.get("filas_errores", 0))
                                        with col3:
                                            st.metric("Estado", final_job.get("estado", "-").title())
                    
                    st.divider()
                    st.info("💡 El proceso ha finalizado. Consulta la pestaña '📋 Trabajos de Importación' para ver más detalles.")

    # ── Jobs List ─────────────────────────────────────────────────────────────
    with tab_jobs:
        col_refresh, col_auto = st.columns([1, 3])
        with col_refresh:
            if st.button("🔄 Refrescar", key="refresh_jobs"):
                st.rerun()
        with col_auto:
            auto_refresh = st.checkbox("Auto-refrescar (cada 5s)", key="auto_refresh_jobs")

        if auto_refresh:
            import time
            time.sleep(5)
            st.rerun()

        data, err = api.list_import_jobs()
        if err:
            st.error(f"❌ Error al cargar trabajos: {err}")
        else:
            jobs = results(data)
            if not jobs:
                st.info("📋 No hay trabajos de importación registrados.")
                st.write("💡 **Para crear uno:** Ve a la pestaña '📤 Subir Archivo' y sube un archivo Excel.")
            else:
                st.subheader(f"📊 Trabajos de Importación ({len(jobs)})")

                # Mostrar resumen general
                estados = {}
                for job in jobs:
                    estado = job.get("estado", "desconocido")
                    estados[estado] = estados.get(estado, 0) + 1

                if estados:
                    st.write("**Resumen por estado:**")
                    cols = st.columns(len(estados))
                    for i, (estado, count) in enumerate(estados.items()):
                        icon = {"completado": "✅", "error": "❌", "validado": "🔍",
                               "validando": "⏳", "importando": "⏳", "subido": "📤"}.get(estado, "⬜")
                        with cols[i]:
                            st.metric(f"{icon} {estado.title()}", count)

                st.divider()

                # Tabla de trabajos
                df = pd.DataFrame(jobs)
                display_cols = [c for c in ["tipo", "estado", "total_filas", "filas_importadas", "filas_errores", "created_at"] if c in df.columns]
                st.dataframe(df[display_cols] if display_cols else df, use_container_width=True, hide_index=True)

                # Detalles de cada trabajo
                for job in jobs:
                    estado = job.get("estado", "")
                    icon = {"completado": "✅", "error": "❌", "validado": "🔍",
                            "validando": "⏳", "importando": "⏳", "subido": "📤"}.get(estado, "⬜")

                    with st.expander(f"{icon} {job.get('tipo','').title()} — {estado.title()} — {job.get('created_at', '')[:16]}"):
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            st.write(f"**ID:** `{job.get('id', '-')}`")
                            st.write(f"**Tipo:** {job.get('tipo', '-').title()}")
                            st.write(f"**Estado:** {estado.title()}")
                        with c2:
                            st.write(f"**Filas Totales:** {job.get('total_filas', '-')}")
                            st.write(f"**Filas Válidas:** {job.get('filas_validas', '-')}")
                            st.write(f"**Filas Importadas:** {job.get('filas_importadas', '-')}")
                        with c3:
                            st.write(f"**Filas con Errores:** {job.get('filas_errores', '-')}")
                            st.write(f"**Filas con Warnings:** {job.get('filas_warnings', '-')}")
                            st.write(f"**Creado:** {job.get('created_at', '-')[:19]}")

                        if job.get("mensaje"):
                            st.info(f"💬 **Mensaje:** {job.get('mensaje')}")

                        # Acciones disponibles
                        acciones = []
                        if estado == "subido":
                            acciones.append(("🔍 Validar", f"val_{job['id']}", "primary"))
                        elif estado == "validado":
                            acciones.append(("📥 Confirmar Importación", f"conf_{job['id']}", "primary"))
                        elif estado in ["validando", "importando"]:
                            acciones.append(("🔄 Refrescar", f"refresh_{job['id']}", "secondary"))

                        # Agregar acciones adicionales según el estado
                        if estado in ("subido", "validado"):
                            acciones.append(("❌ Cancelar", f"canc_{job['id']}", "secondary"))

                        if acciones:
                            st.divider()
                            st.write("**Acciones disponibles:**")
                            cols = st.columns(min(len(acciones), 3))
                            for i, (label, key, button_type) in enumerate(acciones):
                                with cols[i % 3]:
                                    if st.button(label, key=key, type=button_type):
                                        if "Validar" in label:
                                            with st.spinner("Validando datos..."):
                                                r, e = api.validar_import(job["id"])
                                            if e:
                                                st.error(f"❌ Error en validación: {e}")
                                            else:
                                                st.success("✅ Validación iniciada.")
                                        elif "Confirmar" in label:
                                            with st.spinner("Importando datos..."):
                                                r, e = api.confirmar_import(job["id"])
                                            if e:
                                                st.error(f"❌ Error en importación: {e}")
                                            else:
                                                st.success("✅ Importación iniciada.")
                                        elif "Cancelar" in label:
                                            r, e = api.cancelar_import(job["id"])
                                            if e:
                                                st.error(f"❌ Error al cancelar: {e}")
                                            else:
                                                st.success("✅ Trabajo cancelado.")
                                        st.rerun()

                        # Descargas disponibles
                        descargas = []
                        if job.get("reporte_validacion"):
                            content = job["reporte_validacion"]
                            if isinstance(content, dict):
                                content = json.dumps(content, indent=2, ensure_ascii=False)
                            if isinstance(content, str):
                                content = content.encode('utf-8')
                            descargas.append(("📋 Reporte de Validación", content, f"validacion_{job['id']}.txt"))
                        if job.get("reporte_errores"):
                            content = job["reporte_errores"]
                            if isinstance(content, dict):
                                content = json.dumps(content, indent=2, ensure_ascii=False)
                            if isinstance(content, str):
                                content = content.encode('utf-8')
                            descargas.append(("📄 Reporte de Errores", content, f"errores_{job['id']}.txt"))
                        if job.get("archivo_errores"):
                            content = job["archivo_errores"]
                            if isinstance(content, dict):
                                content = json.dumps(content, indent=2, ensure_ascii=False).encode('utf-8')
                            elif isinstance(content, str):
                                content = content.encode('utf-8')
                            descargas.append(("📁 Archivo de Errores", content, f"archivo_errores_{job['id']}.xlsx"))

                        if descargas:
                            st.divider()
                            st.write("**Descargas disponibles:**")
                            cols = st.columns(min(len(descargas), 3))
                            for i, (label, content, filename) in enumerate(descargas):
                                with cols[i % 3]:
                                    st.download_button(
                                        label,
                                        content,
                                        filename,
                                        "text/plain" if filename.endswith('.txt') else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                        key=f"download_{job['id']}_{i}"
                                    )
