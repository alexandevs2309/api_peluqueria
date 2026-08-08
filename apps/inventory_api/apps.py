from django.apps import AppConfig


class InventoryApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.inventory_api'
    
    def ready(self):
        import apps.inventory_api.signals
