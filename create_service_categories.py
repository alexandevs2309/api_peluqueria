#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.services_api.models import ServiceCategory

def create_categories():
    categories = [
        {'name': 'Corte de Cabello', 'description': 'Servicios de corte de cabello'},
        {'name': 'Barba', 'description': 'Servicios de arreglo de barba'},
        {'name': 'Tratamientos', 'description': 'Tratamientos capilares y faciales'},
        {'name': 'Peinado', 'description': 'Servicios de peinado y estilizado'},
        {'name': 'Coloración', 'description': 'Servicios de coloración y tintes'},
        {'name': 'Afeitado', 'description': 'Servicios de afeitado completo'},
        {'name': 'Combo', 'description': 'Paquetes combinados de servicios'},
        {'name': 'Diseños y Detalles', 'description': 'Diseños creativos y detalles especiales'},
        {'name': 'Niños', 'description': 'Servicios especializados para niños'},
        {'name': 'Cejas', 'description': 'Servicios de arreglo y diseño de cejas'},
        {'name': 'Cuidado Facial', 'description': 'Tratamientos y cuidados faciales'},
        {'name': 'Express', 'description': 'Servicios rápidos y express'},
        {'name': 'Premium', 'description': 'Servicios premium y de lujo'},
    ]
    
    for cat_data in categories:
        category, created = ServiceCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={'description': cat_data['description']}
        )
        if created:
            print(f"✅ Categoría creada: {category.name}")
        else:
            print(f"⚠️  Categoría ya existe: {category.name}")

if __name__ == '__main__':
    create_categories()
    print("🎉 Categorías de servicios creadas exitosamente")