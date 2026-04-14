"""Capa de servicios para lógica de negocio de Activos Fijos."""
import logging
from decimal import Decimal
from datetime import date
from django.db import transaction
from django.utils import timezone

from .models import (
    ActivoFijo, MovimientoActivo, MantenimientoActivo,
    BajaActivo, DepreciacionMensual, ProcesoDepreciacion,
)

logger = logging.getLogger(__name__)


def _generar_numero_asiento(empresa):
    """Generar número de asiento correlativo para la empresa."""
    from apps.contabilidad.models import Asiento
    from datetime import datetime
    ultimo = Asiento.objects.filter(empresa=empresa).order_by('-numero_asiento').first()
    if ultimo and ultimo.numero_asiento.isdigit():
        numero = int(ultimo.numero_asiento) + 1
    else:
        numero = int(datetime.now().strftime("%Y%m%d")) * 1000 + 1
    return str(numero).zfill(10)


def _crear_asiento_activo_fijo(empresa, tipo_asiento, fecha, descripcion,
                                lineas, usuario=None, moneda='PYG'):
    """Crea un asiento contable con sus líneas para activos fijos.

    Args:
        lineas: lista de dicts con keys: cuenta, debe, haber, observacion
    Returns:
        Asiento creado o None si no se pudo crear
    """
    from apps.contabilidad.models import Asiento, LineaAsiento

    if not lineas:
        return None

    total_debe = sum(l['debe'] for l in lineas)
    total_haber = sum(l['haber'] for l in lineas)

    if total_debe != total_haber:
        logger.error(f"Asiento desbalanceado: Debe={total_debe}, Haber={total_haber}")
        return None

    numero = _generar_numero_asiento(empresa)
    asiento = Asiento.objects.create(
        empresa=empresa,
        numero_asiento=numero,
        tipo_asiento=tipo_asiento,
        fecha=fecha,
        descripcion=descripcion,
        moneda=moneda,
        total_debe=total_debe,
        total_haber=total_haber,
        estado='registrado',
        usuario_crea=usuario,
    )

    for l in lineas:
        LineaAsiento.objects.create(
            empresa=empresa,
            asiento=asiento,
            cuenta=l['cuenta'],
            debe=l['debe'],
            haber=l['haber'],
            observacion=l.get('observacion', ''),
        )

    return asiento


class ActivoFijoService:
    """Servicio de negocio para operaciones con activos fijos."""

    @staticmethod
    @transaction.atomic
    def dar_de_baja(activo, fecha_baja, motivo, motivo_detalle='',
                    valor_rescate=Decimal('0'), usuario=None, autorizado_por=None):
        """Da de baja un activo fijo con generación de asiento contable."""
        if activo.estado == 'baja':
            raise ValueError('El activo ya está dado de baja.')

        pendientes = activo.mantenimientos.filter(
            estado__in=['programado', 'en_proceso']
        ).count()
        if pendientes > 0:
            raise ValueError(
                f'El activo tiene {pendientes} mantenimiento(s) pendiente(s). '
                'Ciérrelos antes de dar de baja.'
            )

        baja = BajaActivo.objects.create(
            empresa=activo.empresa,
            activo=activo,
            fecha_baja=fecha_baja,
            motivo=motivo,
            motivo_detalle=motivo_detalle,
            valor_rescate=valor_rescate,
            usuario=usuario,
            autorizado_por=autorizado_por,
        )

        activo.estado = 'baja'
        activo.save(update_fields=['estado', 'updated_at'])

        # Generar asiento contable de baja
        ActivoFijoService._generar_asiento_baja(activo, baja, usuario)

        return activo

    @staticmethod
    def _generar_asiento_baja(activo, baja, usuario=None):
        """Genera asiento contable por baja de activo fijo.

        Debe: Dep. Acumulada (por el total acumulado)
        Debe: Banco/Efectivo (valor_rescate) — si hay rescate, va al resultado
        Haber: Activo Fijo (valor adquisición)
        Debe/Haber: Resultado por baja (diferencia)
        """
        cuenta_activo = activo.get_cuenta_activo()
        cuenta_dep = activo.get_cuenta_dep_acumulada()
        cuenta_resultado = activo.get_cuenta_resultado_baja()

        if not all([cuenta_activo, cuenta_dep]):
            logger.warning(
                f"Activo {activo.codigo}: sin cuentas contables, no se genera asiento de baja"
            )
            return None

        dep_acum = activo.depreciacion_acumulada
        valor_adq = activo.valor_adquisicion
        valor_rescate = baja.valor_rescate
        # Resultado = valor_rescate - valor_libro
        valor_libro = valor_adq - dep_acum
        resultado = valor_rescate - valor_libro

        lineas = []
        # Debe: Depreciación acumulada (se revierte)
        if dep_acum > 0:
            lineas.append({
                'cuenta': cuenta_dep,
                'debe': dep_acum,
                'haber': Decimal('0'),
                'observacion': f'Baja {activo.codigo}: reverso dep. acumulada',
            })

        # Haber: Activo Fijo (se da de baja)
        lineas.append({
            'cuenta': cuenta_activo,
            'debe': Decimal('0'),
            'haber': valor_adq,
            'observacion': f'Baja {activo.codigo}: retiro de activo',
        })

        # Resultado por baja (pérdida o ganancia)
        if cuenta_resultado and resultado != 0:
            if resultado < 0:
                # Pérdida
                lineas.append({
                    'cuenta': cuenta_resultado,
                    'debe': abs(resultado),
                    'haber': Decimal('0'),
                    'observacion': f'Baja {activo.codigo}: pérdida por baja',
                })
            else:
                # Ganancia
                lineas.append({
                    'cuenta': cuenta_resultado,
                    'debe': Decimal('0'),
                    'haber': resultado,
                    'observacion': f'Baja {activo.codigo}: ganancia por baja',
                })
        elif resultado != 0 and not cuenta_resultado:
            # Sin cuenta resultado, igualar con valor rescate al debe
            if valor_rescate > 0:
                lineas.append({
                    'cuenta': cuenta_activo,
                    'debe': valor_libro,
                    'haber': Decimal('0'),
                    'observacion': f'Baja {activo.codigo}: ajuste sin cuenta resultado',
                })
                # Reemplazar la línea del activo
                lineas = []
                lineas.append({
                    'cuenta': cuenta_dep,
                    'debe': dep_acum,
                    'haber': Decimal('0'),
                    'observacion': f'Baja {activo.codigo}: reverso dep. acumulada',
                })
                lineas.append({
                    'cuenta': cuenta_activo,
                    'debe': Decimal('0'),
                    'haber': valor_adq,
                    'observacion': f'Baja {activo.codigo}: retiro',
                })
                # Solo balance dep_acum vs valor_adq (sin resultado)
                diff = valor_adq - dep_acum
                if diff > 0:
                    lineas.append({
                        'cuenta': cuenta_activo,
                        'debe': diff,
                        'haber': Decimal('0'),
                        'observacion': f'Baja {activo.codigo}: valor libro pendiente',
                    })

        # Verificar balance antes de crear
        total_d = sum(l['debe'] for l in lineas)
        total_h = sum(l['haber'] for l in lineas)
        if total_d != total_h:
            # Sin cuenta resultado y con desbalance, no generar asiento
            logger.warning(
                f"Activo {activo.codigo}: asiento baja desbalanceado "
                f"(D={total_d}, H={total_h}), se omite"
            )
            return None

        return _crear_asiento_activo_fijo(
            activo.empresa, 'BAJA_ACTIVO', baja.fecha_baja,
            f'Baja de activo {activo.codigo} — {activo.nombre}',
            lineas, usuario, activo.moneda,
        )

    @staticmethod
    @transaction.atomic
    def mover_activo(activo, ubicacion_destino, responsable_nuevo=None,
                     motivo='', usuario=None):
        """Mueve un activo a una nueva ubicación y/o responsable."""
        if activo.estado == 'baja':
            raise ValueError('No se puede mover un activo dado de baja.')

        ubicacion_origen = activo.ubicacion
        responsable_anterior = activo.responsable

        MovimientoActivo.objects.create(
            empresa=activo.empresa,
            activo=activo,
            ubicacion_origen=ubicacion_origen,
            ubicacion_destino=ubicacion_destino,
            responsable_anterior=responsable_anterior,
            responsable_nuevo=responsable_nuevo,
            motivo=motivo,
            usuario_registro=usuario,
        )

        activo.ubicacion = ubicacion_destino
        if responsable_nuevo is not None:
            activo.responsable = responsable_nuevo
        activo.save(update_fields=['ubicacion', 'responsable', 'updated_at'])
        return activo

    @staticmethod
    @transaction.atomic
    def registrar_mantenimiento(activo, tipo, descripcion='', costo=Decimal('0'),
                                proveedor_servicio='', usuario=None):
        """Registra un mantenimiento y cambia el estado del activo si aplica."""
        if activo.estado == 'baja':
            raise ValueError('No se puede registrar mantenimiento en un activo dado de baja.')

        mant = MantenimientoActivo.objects.create(
            empresa=activo.empresa,
            activo=activo,
            tipo=tipo,
            descripcion=descripcion,
            costo=costo,
            proveedor_servicio=proveedor_servicio,
            usuario=usuario,
            estado='programado',
        )

        if activo.estado != 'en_mantenimiento':
            activo.estado = 'en_mantenimiento'
            activo.save(update_fields=['estado', 'updated_at'])

        return mant

    @staticmethod
    @transaction.atomic
    def completar_mantenimiento(mantenimiento, usuario=None):
        """Completa un mantenimiento y verifica si el activo puede volver a 'activo'."""
        if mantenimiento.estado == 'completado':
            raise ValueError('El mantenimiento ya está completado.')

        mantenimiento.estado = 'completado'
        mantenimiento.fecha_fin = timezone.now()
        mantenimiento.save(update_fields=['estado', 'fecha_fin', 'updated_at'])

        activo = mantenimiento.activo
        pendientes = activo.mantenimientos.filter(
            estado__in=['programado', 'en_proceso']
        ).count()
        if pendientes == 0 and activo.estado == 'en_mantenimiento':
            activo.estado = 'activo'
            activo.save(update_fields=['estado', 'updated_at'])

        return mantenimiento

    @staticmethod
    @transaction.atomic
    def calcular_depreciacion_mensual(empresa, anio, mes, usuario=None):
        """Calcula la depreciación mensual con control de secuencialidad y asiento contable.

        Validaciones:
        - No saltar meses (el mes anterior debe estar procesado, excepto el primer mes)
        - No procesar dos veces el mismo mes
        - Excluir activos con propiedad_terceros=True
        """
        # Verificar que no exista ya un proceso para este mes
        if ProcesoDepreciacion.objects.filter(
            empresa=empresa, anio=anio, mes=mes, estado='completado'
        ).exists():
            return 0

        # Control de secuencialidad: verificar mes anterior
        if mes == 1:
            mes_ant, anio_ant = 12, anio - 1
        else:
            mes_ant, anio_ant = mes - 1, anio

        # Solo validar secuencialidad si ya hay algún proceso previo
        hay_procesos_previos = ProcesoDepreciacion.objects.filter(
            empresa=empresa, estado='completado'
        ).exists()

        if hay_procesos_previos:
            mes_ant_ok = ProcesoDepreciacion.objects.filter(
                empresa=empresa, anio=anio_ant, mes=mes_ant, estado='completado'
            ).exists()
            if not mes_ant_ok:
                raise ValueError(
                    f'Debe procesar primero el período {mes_ant:02d}/{anio_ant} '
                    f'antes de calcular {mes:02d}/{anio}.'
                )

        # Crear registro de proceso
        proceso = ProcesoDepreciacion.objects.create(
            empresa=empresa,
            anio=anio,
            mes=mes,
            estado='en_proceso',
            usuario=usuario,
        )

        try:
            activos = ActivoFijo.objects.filter(
                empresa=empresa,
                estado__in=['activo', 'en_mantenimiento'],
                fecha_activacion__isnull=False,
                propiedad_terceros=False,
            ).exclude(
                vida_util_anios=0,
            ).select_related('clasificacion')

            registros_creados = 0
            activos_procesados = 0
            activos_con_error = 0
            lineas_asiento = []
            fecha_periodo = date(anio, mes, 1)

            for activo in activos:
                activos_procesados += 1

                if DepreciacionMensual.objects.filter(
                    empresa=empresa, activo=activo, anio=anio, mes=mes
                ).exists():
                    continue

                if activo.esta_totalmente_depreciado:
                    continue

                if activo.fecha_activacion > fecha_periodo:
                    continue

                monto = activo.depreciacion_mensual
                nueva_acumulada = activo.depreciacion_acumulada + monto
                base_depreciable = activo.valor_adquisicion - activo.valor_residual

                if nueva_acumulada > base_depreciable:
                    monto = base_depreciable - activo.depreciacion_acumulada
                    nueva_acumulada = base_depreciable

                if monto <= 0:
                    continue

                nuevo_valor_libro = activo.valor_adquisicion - nueva_acumulada

                DepreciacionMensual.objects.create(
                    empresa=empresa,
                    activo=activo,
                    anio=anio,
                    mes=mes,
                    monto=monto,
                    depreciacion_acumulada=nueva_acumulada,
                    valor_libro=nuevo_valor_libro,
                )

                activo.depreciacion_acumulada = nueva_acumulada
                activo.valor_libro = nuevo_valor_libro
                activo.save(update_fields=['depreciacion_acumulada', 'valor_libro', 'updated_at'])

                registros_creados += 1

                # Acumular líneas para asiento contable
                cuenta_gasto = activo.get_cuenta_gasto_dep()
                cuenta_dep = activo.get_cuenta_dep_acumulada()
                if cuenta_gasto and cuenta_dep:
                    lineas_asiento.append({
                        'cuenta': cuenta_gasto,
                        'debe': monto,
                        'haber': Decimal('0'),
                        'observacion': f'Dep. {mes:02d}/{anio} — {activo.codigo}',
                    })
                    lineas_asiento.append({
                        'cuenta': cuenta_dep,
                        'debe': Decimal('0'),
                        'haber': monto,
                        'observacion': f'Dep. {mes:02d}/{anio} — {activo.codigo}',
                    })

            # Generar asiento contable consolidado
            asiento = None
            if lineas_asiento:
                asiento = _crear_asiento_activo_fijo(
                    empresa, 'DEPRECIACION', fecha_periodo,
                    f'Depreciación mensual {mes:02d}/{anio}',
                    lineas_asiento, usuario,
                )

            proceso.estado = 'completado'
            proceso.activos_procesados = activos_procesados
            proceso.activos_con_error = activos_con_error
            proceso.registros_creados = registros_creados
            proceso.asiento = asiento
            proceso.fecha_fin = timezone.now()
            proceso.save()

            return registros_creados

        except Exception:
            proceso.estado = 'error'
            proceso.fecha_fin = timezone.now()
            proceso.save()
            raise

    @staticmethod
    def obtener_resumen_activos(empresa):
        """Dashboard KPIs de activos fijos."""
        from django.db.models import Sum, Count, Q
        activos = ActivoFijo.objects.filter(empresa=empresa)

        stats = activos.aggregate(
            total=Count('id'),
            operativos=Count('id', filter=Q(estado='activo')),
            en_mant=Count('id', filter=Q(estado='en_mantenimiento')),
            dados_baja=Count('id', filter=Q(estado='baja')),
            val_adq=Sum('valor_adquisicion', filter=Q(estado__in=['activo', 'en_mantenimiento'])),
            dep_total=Sum('depreciacion_acumulada', filter=Q(estado__in=['activo', 'en_mantenimiento'])),
            val_libro=Sum('valor_libro', filter=Q(estado__in=['activo', 'en_mantenimiento'])),
        )

        return {
            'total_activos': stats['total'] or 0,
            'activos_operativos': stats['operativos'] or 0,
            'en_mantenimiento': stats['en_mant'] or 0,
            'dados_de_baja': stats['dados_baja'] or 0,
            'valor_total_adquisicion': stats['val_adq'] or Decimal('0'),
            'depreciacion_total': stats['dep_total'] or Decimal('0'),
            'valor_libro_total': stats['val_libro'] or Decimal('0'),
        }
