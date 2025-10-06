#!/usr/bin/env python
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from apps.inventory_api.models import Product
from apps.tenants_api.models import Tenant
from django.contrib.auth import get_user_model

User = get_user_model()

def create_sample_products():
    # Obtener el primer tenant (o crear uno si no existe)
    tenant = Tenant.objects.first()
    if not tenant:
        # Crear usuario demo primero
        demo_user = User.objects.create_user(
            email='demo@barberia.com',
            password='demo123',
            full_name='Usuario Demo'
        )
        
        # Crear tenant con owner
        tenant = Tenant.objects.create(
            name="Barbería Demo",
            subdomain="demo",
            owner=demo_user
        )
        
        # Asignar tenant al usuario
        demo_user.tenant = tenant
        demo_user.save()
        
        print(f"✅ Tenant creado: {tenant.name}")
        print(f"✅ Usuario demo creado: {demo_user.email}")

    products_data = [
        {
            'name': 'Shampoo Premium',
            'sku': 'SH001',
            'price': 25.99,
            'stock': 50,
            'category': 'hair-care',
            'description': 'Shampoo profesional para todo tipo de cabello',
            'tenant': tenant
        },
        {
            'name': 'Cera Modeladora',
            'sku': 'CER001', 
            'price': 18.50,
            'stock': 30,
            'category': 'styling',
            'description': 'Cera para peinado con fijación fuerte',
            'tenant': tenant
        },
        {
            'name': 'Aceite para Barba',
            'sku': 'AC001',
            'price': 32.00,
            'stock': 25,
            'category': 'treatments',
            'description': 'Aceite nutritivo para barba',
            'tenant': tenant
        },
        {
            'name': 'Gel Fijador',
            'sku': 'GEL001',
            'price': 15.75,
            'stock': 40,
            'category': 'styling',
            'description': 'Gel de fijación extra fuerte',
            'tenant': tenant
        },
        {
            'name': 'Mascarilla Capilar',
            'sku': 'MAS001',
            'price': 28.90,
            'stock': 20,
            'category': 'treatments',
            'description': 'Mascarilla reparadora intensiva',
            'tenant': tenant
        },
        {
            'name': 'Spray Texturizante',
            'sku': 'SPR001',
            'price': 22.50,
            'stock': 35,
            'category': 'styling',
            'description': 'Spray para dar textura y volumen',
            'tenant': tenant
        }
    ]

    created_count = 0
    for product_data in products_data:
        product, created = Product.objects.get_or_create(
            sku=product_data['sku'],
            tenant=tenant,
            defaults=product_data
        )
        if created:
            created_count += 1
            print(f"✅ Producto creado: {product.name} - Stock: {product.stock}")
        else:
            print(f"⚠️  Producto ya existe: {product.name}")

    print(f"\n🎉 {created_count} productos creados exitosamente!")
    print(f"📦 Total productos en inventario: {Product.objects.filter(tenant=tenant).count()}")

if __name__ == '__main__':
    create_sample_products()