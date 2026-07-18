from django.core.management.base import BaseCommand
from apps.tenants_api.models import Tenant
from apps.settings_api.models import Branch, Setting

class Command(BaseCommand):
    help = 'Crear sucursales por defecto para tenants existentes'

    def handle(self, *args, **options):
        tenants_without_branches = Tenant.objects.filter(branches__isnull=True)
        
        for tenant in tenants_without_branches:
            # Crear sucursal principal
            branch = Branch.objects.create(
                tenant=tenant,
                name=f"{tenant.name} - Principal",
                address="Dirección no configurada",
                is_main=True,
                is_active=True
            )
            
            # Crear configuración básica
            Setting.objects.create(
                branch=branch,
                business_name=tenant.name,
                business_email=tenant.contact_email or "",
                currency="USD",
                timezone="America/Santo_Domingo"
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'✅ Sucursal creada para {tenant.name}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'🎉 Proceso completado. {tenants_without_branches.count()} sucursales creadas.')
        )