"""Página de Activos Fijos — Streamlit frontend."""
import streamlit as st
from datetime import date, datetime
import api_client as api
from helpers import fmt, results, notify_success, notify_error


def render():
    st.title("🏗️ Activos Fijos")

    tabs = st.tabs([
        "📊 Dashboard",
        "📋 Activos",
        "➕ Nuevo Activo",
        "🔧 Mantenimientos",
        "📍 Movimientos",
        "📉 Depreciación",
        "⚙️ Catálogos",
    ])

    with tabs[0]:
        _render_dashboard()
    with tabs[1]:
        _render_lista_activos()
    with tabs[2]:
        _render_nuevo_activo()
    with tabs[3]:
        _render_mantenimientos()
    with tabs[4]:
        _render_movimientos()
    with tabs[5]:
        _render_depreciacion()
    with tabs[6]:
        _render_catalogos()


# ── Dashboard ─────────────────────────────────────────────────────────────────

def _render_dashboard():
    resumen, err = api.get_resumen_activos()
    if err:
        st.warning(f"No se pudo cargar resumen: {err}")
        return

    if not resumen:
        st.info("No hay datos de activos fijos aún.")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Activos", resumen.get('total_activos', 0))
    c2.metric("Operativos", resumen.get('activos_operativos', 0))
    c3.metric("En Mantenimiento", resumen.get('en_mantenimiento', 0))
    c4.metric("Dados de Baja", resumen.get('dados_de_baja', 0))

    st.divider()

    c5, c6, c7 = st.columns(3)
    c5.metric("Valor Adquisición", f"₲ {fmt(resumen.get('valor_total_adquisicion', 0))}")
    c6.metric("Depreciación Acumulada", f"₲ {fmt(resumen.get('depreciacion_total', 0))}")
    c7.metric("Valor en Libros", f"₲ {fmt(resumen.get('valor_libro_total', 0))}")

    st.divider()

    # Alertas
    alertas, err_a = api.get_alertas_activos()
    alertas_list = results(alertas) if not err_a else []
    if alertas_list:
        st.subheader(f"⚠️ Alertas ({len(alertas_list)})")
        for al in alertas_list:
            icon = "🔴" if al['tipo_alerta'] == 'vida_util_superada' else "🟡"
            st.warning(f"{icon} {al['mensaje']}")
    else:
        st.success("✅ Sin alertas activas.")


# ── Lista de Activos ──────────────────────────────────────────────────────────

def _render_lista_activos():
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        buscar = st.text_input("🔍 Buscar", key="af_buscar")
    with col_f2:
        filtro_estado = st.selectbox("Estado", ["", "activo", "en_mantenimiento", "baja"],
                                     format_func=lambda x: "Todos" if x == "" else x.replace("_", " ").title(),
                                     key="af_estado")
    with col_f3:
        filtro_tipo = st.selectbox("Tipo", ["", "IT", "planta", "mobiliario", "vehiculo", "edificio", "terreno", "otro"],
                                   format_func=lambda x: "Todos" if x == "" else x.replace("_", " ").title(),
                                   key="af_tipo")

    data, err = api.list_activos_fijos(search=buscar, estado=filtro_estado, tipo=filtro_tipo)
    activos = results(data)

    if err:
        notify_error(f"Error cargando activos: {err}")
        return

    if not activos:
        st.info("No hay activos fijos registrados. Cree uno en la pestaña '➕ Nuevo Activo'.")
        return

    st.caption(f"Total: {len(activos)} activos")

    for a in activos:
        estado_icon = {"activo": "🟢", "en_mantenimiento": "🟡", "baja": "🔴"}.get(a.get('estado', ''), "⚪")
        with st.expander(f"{estado_icon} {a['codigo']} — {a['nombre']} | {a.get('tipo', '')} | ₲ {fmt(a.get('valor_libro', 0))}"):
            c1, c2, c3 = st.columns(3)
            c1.write(f"**Código:** {a['codigo']}")
            c1.write(f"**Tipo:** {a.get('tipo', '-')}")
            c1.write(f"**Estado:** {a.get('estado', '-')}")
            c2.write(f"**Clasificación:** {a.get('clasificacion_nombre', '-')}")
            c2.write(f"**Ubicación:** {a.get('ubicacion_nombre', '-')}")
            c2.write(f"**Responsable:** {a.get('responsable_nombre', '-')}")
            c3.write(f"**Valor Adquisición:** ₲ {fmt(a.get('valor_adquisicion', 0))}")
            c3.write(f"**Valor en Libros:** ₲ {fmt(a.get('valor_libro', 0))}")
            c3.write(f"**Fecha Adquisición:** {a.get('fecha_adquisicion', '-')}")

            # Detalle completo
            detalle, det_err = api.get_activo_fijo(a['id'])
            if detalle and not det_err:
                st.divider()
                dc1, dc2 = st.columns(2)
                dc1.write(f"**Vida útil:** {detalle.get('vida_util_anios', '-')} años")
                dc1.write(f"**Valor residual:** ₲ {fmt(detalle.get('valor_residual', 0))}")
                dc1.write(f"**Depreciación mensual:** ₲ {fmt(detalle.get('depreciacion_mensual', 0))}")
                dc2.write(f"**% Depreciado:** {detalle.get('porcentaje_depreciado', 0)}%")
                dc2.write(f"**Meses restantes:** {detalle.get('vida_util_restante_meses', 0)}")
                dc2.write(f"**N° Serie:** {detalle.get('numero_serie', '-')}")

                if detalle.get('supera_vida_util'):
                    st.warning("⚠️ Este activo superó su vida útil.")
                if detalle.get('esta_totalmente_depreciado'):
                    st.info("ℹ️ Totalmente depreciado.")

            # Acciones
            if a.get('estado') != 'baja':
                st.divider()
                bc1, bc2 = st.columns(2)
                with bc1:
                    if st.button("📍 Mover", key=f"mover_{a['id']}"):
                        st.session_state[f"mover_modal_{a['id']}"] = True
                with bc2:
                    if st.button("🗑️ Dar de Baja", key=f"baja_{a['id']}", type="primary"):
                        st.session_state[f"baja_modal_{a['id']}"] = True

                # Modal Mover
                if st.session_state.get(f"mover_modal_{a['id']}"):
                    _render_mover_form(a)

                # Modal Baja
                if st.session_state.get(f"baja_modal_{a['id']}"):
                    _render_baja_form(a)


def _render_mover_form(activo):
    st.markdown("**📍 Mover Activo**")
    ubicaciones, _ = api.list_ubicaciones_activo()
    ubs = results(ubicaciones)
    if not ubs:
        st.warning("Cree ubicaciones en la pestaña Catálogos primero.")
        return

    ub_opts = {u['id']: u.get('nombre_completo', f"{u['planta']}") for u in ubs}
    ub_sel = st.selectbox("Ubicación destino", list(ub_opts.keys()),
                          format_func=lambda x: ub_opts[x], key=f"ub_dest_{activo['id']}")
    motivo = st.text_input("Motivo", key=f"motivo_mov_{activo['id']}")

    if st.button("✅ Confirmar Movimiento", key=f"conf_mov_{activo['id']}"):
        data_mov = {"ubicacion_destino": ub_sel, "motivo": motivo}
        res, err = api.mover_activo(activo['id'], data_mov)
        if err:
            notify_error(f"Error: {err}")
        else:
            notify_success(f"Activo {activo['codigo']} movido exitosamente.")
            st.session_state[f"mover_modal_{activo['id']}"] = False
            st.rerun()


def _render_baja_form(activo):
    st.markdown("**🗑️ Dar de Baja**")
    fecha_baja = st.date_input("Fecha de Baja", value=date.today(), key=f"fecha_baja_{activo['id']}")
    motivo = st.selectbox("Motivo", [
        "obsolescencia", "daño_irreparable", "venta", "donacion", "robo", "otro"
    ], format_func=lambda x: x.replace("_", " ").title(), key=f"motivo_baja_{activo['id']}")
    detalle = st.text_area("Detalle", key=f"detalle_baja_{activo['id']}")
    valor_rescate = st.number_input("Valor de Rescate", min_value=0, value=0, key=f"rescate_{activo['id']}")

    if st.button("❌ Confirmar Baja", key=f"conf_baja_{activo['id']}", type="primary"):
        data_baja = {
            "fecha_baja": str(fecha_baja),
            "motivo": motivo,
            "motivo_detalle": detalle,
            "valor_rescate": str(valor_rescate),
        }
        res, err = api.dar_baja_activo(activo['id'], data_baja)
        if err:
            notify_error(f"Error: {err}")
        else:
            notify_success(f"Activo {activo['codigo']} dado de baja.")
            st.session_state[f"baja_modal_{activo['id']}"] = False
            st.rerun()


# ── Nuevo Activo ──────────────────────────────────────────────────────────────

def _render_nuevo_activo():
    st.subheader("➕ Registrar Nuevo Activo Fijo")

    # Cargar catálogos
    clasificaciones, _ = api.list_clasificaciones_activo()
    ubicaciones, _ = api.list_ubicaciones_activo()
    centros_costo, _ = api.list_centros_costo()
    proveedores, _ = api.list_proveedores()

    cls_list = results(clasificaciones)
    ub_list = results(ubicaciones)
    cc_list = results(centros_costo)
    prov_list = results(proveedores)

    with st.form("form_nuevo_activo", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            codigo = st.text_input("Código *")
            nombre = st.text_input("Nombre *")
            tipo = st.selectbox("Tipo", [
                "IT", "planta", "mobiliario", "vehiculo", "edificio", "terreno", "otro"
            ], format_func=lambda x: {
                "IT": "IT / Tecnología", "planta": "Planta / Maquinaria",
                "mobiliario": "Mobiliario", "vehiculo": "Vehículo",
                "edificio": "Edificio", "terreno": "Terreno", "otro": "Otro"
            }.get(x, x))
            descripcion = st.text_area("Descripción")

        with c2:
            valor_adquisicion = st.number_input("Valor de Adquisición *", min_value=0, value=0)
            valor_residual = st.number_input("Valor Residual", min_value=0, value=0)
            vida_util = st.number_input("Vida Útil (años)", min_value=1, max_value=100, value=5)
            fecha_adquisicion = st.date_input("Fecha de Adquisición", value=date.today())

        c3, c4 = st.columns(2)
        with c3:
            # Clasificación
            cls_opts = {None: "-- Sin clasificación --"}
            for c in cls_list:
                cls_opts[c['id']] = c['nombre']
            clasificacion = st.selectbox("Clasificación", list(cls_opts.keys()),
                                         format_func=lambda x: cls_opts[x])
            # Ubicación
            ub_opts = {None: "-- Sin ubicación --"}
            for u in ub_list:
                ub_opts[u['id']] = u.get('nombre_completo', u['planta'])
            ubicacion = st.selectbox("Ubicación", list(ub_opts.keys()),
                                     format_func=lambda x: ub_opts[x])
        with c4:
            # Centro de costo
            cc_opts = {None: "-- Sin centro de costo --"}
            for cc in cc_list:
                cc_opts[cc['id']] = f"{cc['codigo']} - {cc['descripcion']}"
            centro_costo = st.selectbox("Centro de Costo", list(cc_opts.keys()),
                                        format_func=lambda x: cc_opts[x])
            # Proveedor
            prov_opts = {None: "-- Sin proveedor --"}
            for p in prov_list:
                prov_opts[p['id']] = p.get('nombre', str(p['id']))
            proveedor = st.selectbox("Proveedor", list(prov_opts.keys()),
                                     format_func=lambda x: prov_opts[x])

        c5, c6 = st.columns(2)
        with c5:
            numero_serie = st.text_input("Número de Serie")
        with c6:
            numero_factura = st.text_input("Número de Factura")

        notas = st.text_area("Notas")

        submitted = st.form_submit_button("💾 Crear Activo Fijo", type="primary")

    if submitted:
        if not codigo or not nombre:
            notify_error("Código y Nombre son obligatorios.")
            return
        if valor_adquisicion <= 0:
            notify_error("El valor de adquisición debe ser mayor a 0.")
            return

        payload = {
            "codigo": codigo.strip(),
            "nombre": nombre.strip(),
            "tipo": tipo,
            "descripcion": descripcion,
            "valor_adquisicion": str(valor_adquisicion),
            "valor_residual": str(valor_residual),
            "vida_util_anios": vida_util,
            "fecha_adquisicion": str(fecha_adquisicion),
            "numero_serie": numero_serie,
            "numero_factura": numero_factura,
            "notas": notas,
        }
        if clasificacion:
            payload["clasificacion"] = clasificacion
        if ubicacion:
            payload["ubicacion"] = ubicacion
        if centro_costo:
            payload["centro_costo"] = centro_costo
        if proveedor:
            payload["proveedor"] = proveedor

        res, err = api.create_activo_fijo(payload)
        if err:
            notify_error(f"Error creando activo: {err}")
        else:
            notify_success(f"Activo {codigo} creado exitosamente.")
            st.rerun()


# ── Mantenimientos ────────────────────────────────────────────────────────────

def _render_mantenimientos():
    st.subheader("🔧 Mantenimientos")

    # Listar mantenimientos
    data, err = api.list_mantenimientos_activo()
    mants = results(data)

    if mants:
        for m in mants:
            estado_icon = {
                "programado": "📅", "en_proceso": "🔄",
                "completado": "✅", "cancelado": "❌"
            }.get(m.get('estado', ''), "⚪")

            with st.expander(f"{estado_icon} {m.get('activo_codigo', '')} — {m.get('tipo', '').title()} | {m.get('estado', '')} | {m.get('fecha', '')[:10]}"):
                st.write(f"**Activo:** {m.get('activo_codigo', '')} - {m.get('activo_nombre', '')}")
                st.write(f"**Tipo:** {m.get('tipo', '-')}")
                st.write(f"**Estado:** {m.get('estado', '-')}")
                st.write(f"**Descripción:** {m.get('descripcion', '-')}")
                st.write(f"**Costo:** ₲ {fmt(m.get('costo', 0))}")
                st.write(f"**Proveedor Servicio:** {m.get('proveedor_servicio', '-')}")

                if m.get('estado') in ['programado', 'en_proceso']:
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button("✅ Completar", key=f"comp_mant_{m['id']}"):
                            res, err = api.completar_mantenimiento(m['id'])
                            if err:
                                notify_error(f"Error: {err}")
                            else:
                                notify_success("Mantenimiento completado.")
                                st.rerun()
                    with bc2:
                        if st.button("❌ Cancelar", key=f"canc_mant_{m['id']}"):
                            res, err = api.cancelar_mantenimiento(m['id'])
                            if err:
                                notify_error(f"Error: {err}")
                            else:
                                notify_success("Mantenimiento cancelado.")
                                st.rerun()

    # Formulario nuevo mantenimiento
    st.divider()
    st.markdown("**➕ Nuevo Mantenimiento**")

    activos_data, _ = api.list_activos_fijos(estado="activo")
    activos_mant, _ = api.list_activos_fijos(estado="en_mantenimiento")
    activos_all = results(activos_data) + results(activos_mant)

    if not activos_all:
        st.info("No hay activos disponibles para mantenimiento.")
        return

    act_opts = {a['id']: f"{a['codigo']} - {a['nombre']}" for a in activos_all}

    with st.form("form_nuevo_mant", clear_on_submit=True):
        activo_sel = st.selectbox("Activo", list(act_opts.keys()),
                                  format_func=lambda x: act_opts[x])
        tipo_mant = st.selectbox("Tipo", ["preventivo", "correctivo"],
                                 format_func=lambda x: x.title())
        desc_mant = st.text_area("Descripción")
        costo_mant = st.number_input("Costo", min_value=0, value=0)
        prov_mant = st.text_input("Proveedor de Servicio")

        if st.form_submit_button("🔧 Registrar Mantenimiento", type="primary"):
            payload = {
                "activo": activo_sel,
                "tipo": tipo_mant,
                "descripcion": desc_mant,
                "costo": str(costo_mant),
                "proveedor_servicio": prov_mant,
            }
            res, err = api.create_mantenimiento_activo(payload)
            if err:
                notify_error(f"Error: {err}")
            else:
                notify_success("Mantenimiento registrado.")
                st.rerun()


# ── Movimientos ───────────────────────────────────────────────────────────────

def _render_movimientos():
    st.subheader("📍 Historial de Movimientos")

    data, err = api.list_movimientos_activo()
    movs = results(data)

    if not movs:
        st.info("No hay movimientos registrados.")
        return

    for m in movs:
        st.markdown(
            f"**{m.get('fecha', '')[:10]}** — "
            f"`{m.get('activo_codigo', '')}` "
            f"{m.get('ubicacion_origen_nombre', '?')} → {m.get('ubicacion_destino_nombre', '?')}"
        )
        if m.get('motivo'):
            st.caption(f"Motivo: {m['motivo']}")
        st.divider()


# ── Depreciación ──────────────────────────────────────────────────────────────

def _render_depreciacion():
    st.subheader("📉 Depreciación")

    # Calcular depreciación
    with st.expander("🔄 Calcular Depreciación Mensual"):
        c1, c2 = st.columns(2)
        with c1:
            anio_dep = st.number_input("Año", min_value=2020, max_value=2050,
                                       value=date.today().year, key="dep_anio")
        with c2:
            mes_dep = st.number_input("Mes", min_value=1, max_value=12,
                                      value=date.today().month, key="dep_mes")

        if st.button("📊 Calcular", type="primary"):
            res, err = api.calcular_depreciacion({"anio": anio_dep, "mes": mes_dep})
            if err:
                notify_error(f"Error: {err}")
            else:
                notify_success(f"{res.get('mensaje', 'OK')} — {res.get('registros_creados', 0)} registros.")

    # Reporte
    st.divider()
    st.markdown("**📋 Reporte de Depreciación**")
    c1, c2 = st.columns(2)
    with c1:
        anio_rep = st.number_input("Año", min_value=2020, max_value=2050,
                                   value=date.today().year, key="rep_anio")
    with c2:
        mes_rep = st.selectbox("Mes", [""] + list(range(1, 13)),
                               format_func=lambda x: "Todos" if x == "" else str(x),
                               key="rep_mes")

    data, err = api.list_depreciaciones(anio=str(anio_rep), mes=str(mes_rep) if mes_rep else "")
    deps = results(data)

    if deps:
        import pandas as pd
        df = pd.DataFrame(deps)
        cols_show = ['activo_codigo', 'anio', 'mes', 'monto', 'depreciacion_acumulada', 'valor_libro']
        cols_available = [c for c in cols_show if c in df.columns]
        st.dataframe(df[cols_available], use_container_width=True)

        total = sum(float(d.get('monto', 0)) for d in deps)
        st.caption(f"**Total depreciación del período:** ₲ {fmt(total)}")
    else:
        st.info("No hay registros de depreciación para el período seleccionado.")


# ── Catálogos ─────────────────────────────────────────────────────────────────

def _render_catalogos():
    st.subheader("⚙️ Catálogos de Activos Fijos")

    cat_tabs = st.tabs(["📂 Clasificaciones", "📍 Ubicaciones", "💰 Centros de Costo"])

    with cat_tabs[0]:
        _render_clasificaciones()
    with cat_tabs[1]:
        _render_ubicaciones()
    with cat_tabs[2]:
        _render_centros_costo()


def _render_clasificaciones():
    data, err = api.list_clasificaciones_activo()
    cls_list = results(data)

    if cls_list:
        for c in cls_list:
            col1, col2 = st.columns([4, 1])
            col1.write(f"**{c['nombre']}** — Vida útil default: {c.get('vida_util_default', '-')} años")
            if c.get('descripcion'):
                col1.caption(c['descripcion'])
            with col2:
                if st.button("🗑️", key=f"del_cls_{c['id']}"):
                    ok, err = api.delete_clasificacion_activo(c['id'])
                    if ok:
                        notify_success("Clasificación eliminada.")
                        st.rerun()
                    else:
                        notify_error(f"Error: {err}")

    with st.form("form_nueva_cls", clear_on_submit=True):
        st.markdown("**➕ Nueva Clasificación**")
        nombre_cls = st.text_input("Nombre")
        desc_cls = st.text_input("Descripción")
        vida_cls = st.number_input("Vida Útil Default (años)", min_value=1, value=5)

        if st.form_submit_button("Crear"):
            if nombre_cls:
                res, err = api.create_clasificacion_activo({
                    "nombre": nombre_cls.strip(),
                    "descripcion": desc_cls,
                    "vida_util_default": vida_cls,
                })
                if err:
                    notify_error(f"Error: {err}")
                else:
                    notify_success(f"Clasificación '{nombre_cls}' creada.")
                    st.rerun()


def _render_ubicaciones():
    data, err = api.list_ubicaciones_activo()
    ub_list = results(data)

    if ub_list:
        for u in ub_list:
            col1, col2 = st.columns([4, 1])
            col1.write(f"**{u.get('nombre_completo', u['planta'])}**")
            with col2:
                if st.button("🗑️", key=f"del_ub_{u['id']}"):
                    ok, err = api.delete_ubicacion_activo(u['id'])
                    if ok:
                        notify_success("Ubicación eliminada.")
                        st.rerun()
                    else:
                        notify_error(f"Error: {err}")

    with st.form("form_nueva_ub", clear_on_submit=True):
        st.markdown("**➕ Nueva Ubicación**")
        planta = st.text_input("Planta *")
        edificio = st.text_input("Edificio")
        area = st.text_input("Área")

        if st.form_submit_button("Crear"):
            if planta:
                res, err = api.create_ubicacion_activo({
                    "planta": planta.strip(),
                    "edificio": edificio.strip(),
                    "area": area.strip(),
                })
                if err:
                    notify_error(f"Error: {err}")
                else:
                    notify_success("Ubicación creada.")
                    st.rerun()


def _render_centros_costo():
    data, err = api.list_centros_costo()
    cc_list = results(data)

    if cc_list:
        for cc in cc_list:
            col1, col2 = st.columns([4, 1])
            col1.write(f"**{cc['codigo']}** — {cc.get('descripcion', '')}")
            with col2:
                if st.button("🗑️", key=f"del_cc_{cc['id']}"):
                    ok, err = api.delete_centro_costo(cc['id'])
                    if ok:
                        notify_success("Centro de costo eliminado.")
                        st.rerun()
                    else:
                        notify_error(f"Error: {err}")

    with st.form("form_nuevo_cc", clear_on_submit=True):
        st.markdown("**➕ Nuevo Centro de Costo**")
        codigo_cc = st.text_input("Código *")
        desc_cc = st.text_input("Descripción")

        if st.form_submit_button("Crear"):
            if codigo_cc:
                res, err = api.create_centro_costo({
                    "codigo": codigo_cc.strip(),
                    "descripcion": desc_cc.strip(),
                })
                if err:
                    notify_error(f"Error: {err}")
                else:
                    notify_success(f"Centro de costo '{codigo_cc}' creado.")
                    st.rerun()
