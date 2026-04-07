"""Configuración de la aplicación de contabilidad."""
from django.apps import AppConfig


class ContabilidadConfig(AppConfig):
    """Configuración para módulo de contabilidad."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.contabilidad'
    verbose_name = 'Contabilidad'
    
    def ready(self):
        """Importar signals al cargar la aplicación."""
        import apps.contabilidad.signals
