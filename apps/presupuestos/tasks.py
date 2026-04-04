"""Tasks for presupuestos app (email, WhatsApp, etc.)."""
import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from .models import Presupuesto

logger = logging.getLogger(__name__)


def enviar_presupuesto_email(presupuesto_id):
    """Send presupuesto via email."""
    try:
        presupuesto = Presupuesto.objects.get(id=presupuesto_id)
        
        # Context for email template
        context = {
            'presupuesto': presupuesto,
            'empresa': presupuesto.empresa,
            'cliente': presupuesto.cliente,
            'detalles': presupuesto.detalles.all(),
            'fecha_vigencia': presupuesto.fecha_vigencia,
            'condiciones_pago': presupuesto.condiciones_pago,
        }
        
        # Render HTML email
        html_message = render_to_string('presupuestos/email_presupuesto.html', context)
        
        # Create email
        email = EmailMessage(
            subject=f"Presupuesto {presupuesto.numero} - {presupuesto.empresa.nombre}",
            body="Por favor abra este email con soporte para HTML.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[presupuesto.email_cliente],
        )
        email.attach_alternative(html_message, "text/html")
        
        # Send
        email.send(fail_silently=False)
        logger.info(f"[presupuestos] Presupuesto {presupuesto.id} enviado por email a {presupuesto.email_cliente}")
        
        return True
    except Exception as e:
        logger.exception(f"[presupuestos] Error enviando presupuesto {presupuesto_id} por email: {e}")
        raise


def enviar_presupuesto_whatsapp(presupuesto_id):
    """Send presupuesto via WhatsApp."""
    try:
        presupuesto = Presupuesto.objects.get(id=presupuesto_id)
        
        # Format message
        mensaje = f"""
Hola {presupuesto.cliente.nombre},

Aquellos el presupuesto {presupuesto.numero}

*Detalle:*
"""
        for detalle in presupuesto.detalles.all():
            mensaje += f"\n• {detalle.descripcion}: {detalle.cantidad} x {detalle.precio_unitario} = {detalle.total}"
        
        mensaje += f"\n\n*Subtotal:* ₲ {presupuesto.subtotal:,.0f}"
        mensaje += f"\n*Impuesto:* ₲ {presupuesto.total_impuesto:,.0f}"
        mensaje += f"\n*Total:* ₲ {presupuesto.total:,.0f}"
        
        if presupuesto.fecha_vigencia:
            mensaje += f"\n*Vigencia:* hasta {presupuesto.fecha_vigencia}"
        
        if presupuesto.condiciones_pago:
            mensaje += f"\n*Condiciones:* {presupuesto.condiciones_pago}"
        
        # TODO: Integrate with WhatsApp API (Twilio, Meta, MessageBird, etc.)
        # For now, just log it
        logger.info(f"[presupuestos] Presupuesto {presupuesto.id} mensaje WhatsApp a {presupuesto.telefono_cliente}:")
        logger.info(f"[presupuestos] {mensaje}")
        
        # Example with Twilio (uncomment if available):
        # from twilio.rest import Client
        # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        # message = client.messages.create(
        #     from_=settings.TWILIO_PHONE_NUMBER,
        #     to=presupuesto.telefono_cliente,
        #     body=mensaje
        # )
        
        return True
    except Exception as e:
        logger.exception(f"[presupuestos] Error enviando presupuesto {presupuesto_id} por WhatsApp: {e}")
        raise


def generar_pdf_presupuesto(presupuesto_id):
    """Generate presupuesto as PDF."""
    try:
        presupuesto = Presupuesto.objects.get(id=presupuesto_id)
        # TODO: Implement PDF generation using reportlab or weasyprint
        logger.info(f"[presupuestos] Generando PDF para presupuesto {presupuesto_id}")
        return True
    except Exception as e:
        logger.exception(f"[presupuestos] Error generando PDF para presupuesto {presupuesto_id}: {e}")
        raise
