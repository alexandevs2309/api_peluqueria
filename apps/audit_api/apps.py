from django.apps import AppConfig


class AuditApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.audit_api'
    
    def ready(self):
        """Import signals when the app is ready"""
        import apps.audit_api.signals
