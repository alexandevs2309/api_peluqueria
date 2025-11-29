from django.apps import AppConfig

class NotificationsApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.notifications_api'

    def ready(self):
        import apps.notifications_api.signals