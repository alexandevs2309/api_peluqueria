from django.core.management.base import BaseCommand
from apps.services_api.models import ServiceCategory
from apps.inventory_api.models import ProductCategory
from apps.tenants_api.models import Tenant


class Command(BaseCommand):
    help = 'Crear categorias de servicios y productos por defecto para todos los tenants'

    DEFAULT_SERVICE_CATEGORIES = [
        {'name': 'Corte de Cabello', 'description': 'Servicios de corte de cabello'},
        {'name': 'Barba', 'description': 'Servicios de arreglo y diseño de barba'},
        {'name': 'Afeitado', 'description': 'Servicios de afeitado clásico'},
        {'name': 'Tratamientos', 'description': 'Tratamientos capilares y de cuero cabelludo'},
        {'name': 'Peinado', 'description': 'Servicios de peinado y estilizado'},
        {'name': 'Coloración', 'description': 'Tintes, mechas y coloración'},
        {'name': 'Keratina', 'description': 'Tratamientos de keratina y alisado'},
        {'name': 'Cejas', 'description': 'Diseño y depilación de cejas'},
        {'name': 'Masaje Capilar', 'description': 'Masajes de cuero cabelludo'},
        {'name': 'Extensiones', 'description': 'Colocación de extensiones de cabello'},
        {'name': 'Combo', 'description': 'Paquetes y servicios combinados'},
    ]

    DEFAULT_PRODUCT_CATEGORIES = [
        {'name': 'Productos de Cabello', 'description': 'Shampoos, acondicionadores y tratamientos'},
        {'name': 'Productos de Barba', 'description': 'Aceites, bálsamos y ceras para barba'},
        {'name': 'Colorantes', 'description': 'Tintes y productos de coloración'},
        {'name': 'Herramientas de Corte', 'description': 'Tijeras, navajas y maquinillas'},
        {'name': 'Equipos Eléctricos', 'description': 'Secadores, planchas y rizadores'},
        {'name': 'Accesorios', 'description': 'Peines, cepillos y capas'},
        {'name': 'Higiene y Desinfección', 'description': 'Productos de limpieza y esterilización'},
        {'name': 'Retail', 'description': 'Productos para venta al cliente'},
    ]

    def handle(self, *args, **options):
        tenants = Tenant.objects.filter(is_active=True)

        for tenant in tenants:
            self.stdout.write(f'Procesando tenant: {tenant.name}')

            for cat in self.DEFAULT_SERVICE_CATEGORIES:
                _, created = ServiceCategory.objects.get_or_create(
                    name=cat['name'], tenant=tenant,
                    defaults={'description': cat['description']}
                )
                status = 'Creada' if created else 'Ya existe'
                self.stdout.write(f'  [Servicio] {status}: {cat["name"]}')

            for cat in self.DEFAULT_PRODUCT_CATEGORIES:
                _, created = ProductCategory.objects.get_or_create(
                    name=cat['name'], tenant=tenant,
                    defaults={'description': cat['description']}
                )
                status = 'Creada' if created else 'Ya existe'
                self.stdout.write(f'  [Producto] {status}: {cat["name"]}')

        self.stdout.write(self.style.SUCCESS('Categorias creadas exitosamente'))
