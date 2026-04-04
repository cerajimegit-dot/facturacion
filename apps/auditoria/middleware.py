"""Audit middleware to log API actions."""
import json
import logging
import uuid as uuid_mod
from decimal import Decimal
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('apps.auditoria')


class _SafeEncoder(json.JSONEncoder):
    """JSON encoder that handles UUID, Decimal, and other non-serializable types."""
    def default(self, obj):
        if isinstance(obj, uuid_mod.UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return str(obj)
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


class AuditMiddleware(MiddlewareMixin):
    """Middleware that logs write operations (POST, PUT, PATCH, DELETE) to the audit trail."""

    AUDIT_METHODS = ('POST', 'PUT', 'PATCH', 'DELETE')
    SKIP_PATHS = ('/api/v1/auth/login/', '/api/v1/auth/token/refresh/', '/api/schema/')

    @staticmethod
    def _safe_serialize(data):
        if isinstance(data, dict):
            return {k: AuditMiddleware._safe_serialize(v) for k, v in data.items()}
        if isinstance(data, list):
            return [AuditMiddleware._safe_serialize(v) for v in data]
        if isinstance(data, tuple):
            return [AuditMiddleware._safe_serialize(v) for v in data]
        if isinstance(data, uuid_mod.UUID):
            return str(data)
        if isinstance(data, Decimal):
            return str(data)
        if isinstance(data, (int, float, str, bool)) or data is None:
            return data
        try:
            return json.loads(json.dumps(data, cls=_SafeEncoder))
        except Exception:
            return str(data)

    def process_response(self, request, response):
        if request.method not in self.AUDIT_METHODS:
            return response
        if any(request.path.startswith(p) for p in self.SKIP_PATHS):
            return response
        if not hasattr(request, 'user') or not request.user.is_authenticated:
            return response
        if response.status_code >= 400:
            return response

        try:
            from .models import Auditoria

            accion_map = {
                'POST': 'crear',
                'PUT': 'actualizar',
                'PATCH': 'actualizar',
                'DELETE': 'eliminar',
            }
            accion = accion_map.get(request.method, 'actualizar')

            # Extract model info from path
            path_parts = [p for p in request.path.split('/') if p]
            modelo = path_parts[2] if len(path_parts) > 2 else 'unknown'

            # Try to get empresa from request data
            empresa_id = None
            if hasattr(request, 'data') and isinstance(request.data, dict):
                empresa_id = request.data.get('empresa')
            if not empresa_id:
                empresa_id = request.GET.get('empresa')
            if empresa_id:
                empresa_id = str(empresa_id)

            # Try to extract object id from response
            objeto_id = ''
            if hasattr(response, 'data') and isinstance(response.data, dict):
                objeto_id = str(response.data.get('id', ''))

            datos_nuevos = None
            if hasattr(response, 'data'):
                try:
                    raw = response.data
                    datos_nuevos = AuditMiddleware._safe_serialize(raw)
                except Exception:
                    logger.exception("Error serializing datos_nuevos in audit middleware")
                    datos_nuevos = None

            ip = self._get_client_ip(request)

            Auditoria.objects.create(
                usuario=request.user,
                empresa_id=empresa_id,
                accion=accion,
                modelo=modelo,
                objeto_id=objeto_id,
                datos_nuevos=datos_nuevos,
                ip_address=ip,
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
                descripcion=f"{request.method} {request.path}",
            )
        except Exception as e:
            logger.exception(f"Error in audit middleware: {e}")

        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')
