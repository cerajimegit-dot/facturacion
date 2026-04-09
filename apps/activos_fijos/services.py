"""Capa de servicios para lógica de negocio de Activos Fijos."""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import (
    ActivoFijo, MovimientoActivo, MantenimientoActivo,
    BajaActivo, DepreciacionMensual,
)


class ActivoFijoService:
    """Servicio de negocio para operaciones con activos fijos."""

    @staticmethod
    @transaction.atomic
    def dar_de_baja(activo, fecha_baja, motivo, motivo_detalle='',
                    valor_rescate=Decimal('0'), usuario=None, autorizado_por=None):
        """Da de baja un activo fijo.

        - Valida que no esté ya de baja
        - Crea registro de BajaActivo
        - Cambia estado del activo a 'baja'
        - Bloquea modificaciones posteriores
        """
        if activo.estado == 'baja':
            raise ValueError('El activo ya está dado de baja.')

        # Validar que no tenga mantenimientos pendientes
        pendientes = activo.mantenimientos.filter(
            estado__in=['programado', 'en_proceso']
        ).count()
        if pendientes > 0:
            raise ValueError(
                f'El activo tiene {pendientes} mantenimiento(s) pendiente(s). '
                'Ciérrelos antes de dar de baja.'
            )

        BajaActivo.objects.create(
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
        return activo

    @staticmethod
    @transaction.atomic
    def mover_activo(activo, ubicacion_destino, responsable_nuevo=None,
                     motivo='', usuario=None):
        """Mueve un activo a una nueva ubicación y/o responsable.

        - Registra en HistorialMovimientos
        - Actualiza ubicación y responsable del activo
        """
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

        # Cambiar estado a en_mantenimiento si no está ya
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

        # Si no quedan mantenimientos pendientes, volver a activo
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
    def calcular_depreciacion_mensual(empresa, anio, mes):
        """Calcula la depreciación mensual para todos los activos activos de la empresa.

        Método: Línea recta
        Fórmula: (Valor Adquisición - Valor Residual) / (Vida Útil en meses)
        """
        activos = ActivoFijo.objects.filter(
            empresa=empresa,
            estado__in=['activo', 'en_mantenimiento'],
            fecha_activacion__isnull=False,
        ).exclude(
            vida_util_anios=0,
        )

        registros_creados = 0
        for activo in activos:
            # Verificar si ya existe registro para este mes
            if DepreciacionMensual.objects.filter(
                empresa=empresa, activo=activo, anio=anio, mes=mes
            ).exists():
                continue

            # Verificar que el activo esté dentro de su vida útil
            if activo.esta_totalmente_depreciado:
                continue

            # Verificar que la fecha de activación sea anterior al período
            from datetime import date
            fecha_periodo = date(anio, mes, 1)
            if activo.fecha_activacion > fecha_periodo:
                continue

            monto = activo.depreciacion_mensual
            nueva_acumulada = activo.depreciacion_acumulada + monto
            base_depreciable = activo.valor_adquisicion - activo.valor_residual

            # No depreciar más allá del valor depreciable
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

            # Actualizar el activo
            activo.depreciacion_acumulada = nueva_acumulada
            activo.valor_libro = nuevo_valor_libro
            activo.save(update_fields=['depreciacion_acumulada', 'valor_libro', 'updated_at'])

            registros_creados += 1

        return registros_creados

    @staticmethod
    def obtener_resumen_activos(empresa):
        """Genera resumen/KPIs de activos fijos."""
        from django.db.models import Sum, Count, Q

        activos = ActivoFijo.objects.filter(empresa=empresa)

        total_activos = activos.count()
        activos_operativos = activos.filter(estado='activo').count()
        en_mantenimiento = activos.filter(estado='en_mantenimiento').count()
        dados_de_baja = activos.filter(estado='baja').count()

        valores = activos.exclude(estado='baja').aggregate(
            valor_total_adquisicion=Sum('valor_adquisicion'),
            depreciacion_total=Sum('depreciacion_acumulada'),
            valor_libro_total=Sum('valor_libro'),
        )

        # Activos que superan vida útil
        from dateutil.relativedelta import relativedelta
        hoy = timezone.now().date()
        alerta_vida_util = 0
        for a in activos.filter(estado__in=['activo', 'en_mantenimiento'], fecha_activacion__isnull=False):
            fecha_fin = a.fecha_activacion + relativedelta(years=a.vida_util_anios)
            if hoy > fecha_fin:
                alerta_vida_util += 1

        # Mantenimientos pendientes
        mant_pendientes = MantenimientoActivo.objects.filter(
            empresa=empresa,
            estado__in=['programado', 'en_proceso'],
        ).count()

        return {
            'total_activos': total_activos,
            'activos_operativos': activos_operativos,
            'en_mantenimiento': en_mantenimiento,
            'dados_de_baja': dados_de_baja,
            'valor_total_adquisicion': valores['valor_total_adquisicion'] or Decimal('0'),
            'depreciacion_total': valores['depreciacion_total'] or Decimal('0'),
            'valor_libro_total': valores['valor_libro_total'] or Decimal('0'),
            'alerta_vida_util': alerta_vida_util,
            'mantenimientos_pendientes': mant_pendientes,
        }
