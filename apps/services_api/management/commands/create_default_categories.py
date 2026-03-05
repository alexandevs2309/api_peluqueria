from django.core.management.base import BaseCommand
from apps.services_api.models import ServiceCategory
from apps.tenants_api.models import Tenant


class Command(BaseCommand):
    help = 'Crear categorias de servicios por defecto para todos los tenants'

    def handle(self, *args, **options):
        categorias_default = [
            {'name': 'Corte de Cabello', 'description': 'Servicios de corte de cabello'},
            {'name': 'Barba', 'description': 'Servicios de arreglo de barba'},
            {'name': 'Tratamientos', 'description': 'Tratamientos capilares'},
            {'name': 'Peinado', 'description': 'Servicios de peinado'},
            {'name': 'Coloracion', 'description': 'Servicios de coloracion'},
            {'name': 'Afeitado', 'description': 'Servicios de afeitado'},
            {'name': 'Combo', 'description': 'Paquetes combinados'},
        ]

        tenants = Tenant.objects.filter(is_active=True)
        
        for tenant in tenants:
            self.stdout.write(f'Procesando tenant: {tenant.name}')
            
            for cat_data in categorias_default:
                categoria, created = ServiceCategory.objects.get_or_create(
                    name=cat_data['name'],
                    tenant=tenant,
                    defaults={'description': cat_data['description']}
                )
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f'  Creada: {categoria.name}'))
                else:
                    self.stdout.write(f'  Ya existe: {categoria.name}')
        
        self.stdout.write(self.style.SUCCESS('Categorias creadas exitosamente'))
