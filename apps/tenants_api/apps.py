from django.apps import AppConfig

class TenantsApiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.tenants_api'

    def ready(self):
        # FORCE RLS también afecta al propietario: las migraciones necesitan
        # un bypass explícito y temporal sobre su propia conexión.
        from apps.core.rls_internal import connect_migration_bypass

        connect_migration_bypass()
