from django.apps import AppConfig


class EmployeesApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.employees_api'
    
    def ready(self):
        # Importar signals para registrarlos
        try:
            import apps.employees_api.signals
        except ImportError:
            pass
