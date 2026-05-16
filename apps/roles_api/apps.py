from django.apps import AppConfig


class RolesApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.roles_api'

    def ready(self):
        import apps.roles_api.signals  # noqa: F401
