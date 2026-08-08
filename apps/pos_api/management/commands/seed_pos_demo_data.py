import os
from django.core.management.base import BaseCommand
from apps.tenants_api.models import Tenant
from apps.services_api.models import Service, ServiceCategory
from apps.inventory_api.models import Product, ProductCategory
from apps.clients_api.models import Client

class Command(BaseCommand):
    help = 'Puebla el POS con clientes, productos y servicios de Barbería/Peluquería con imágenes de alta calidad y captions.'

    def handle(self, *args, **options):
        tenant = Tenant.objects.first()
        if not tenant:
            self.stderr.write("No se encontró ningún Tenant activo en la base de datos.")
            return

        self.stdout.write(f"Poblando datos demo para Tenant: {tenant.name} (ID {tenant.id})...")

        # 1. Clientes Reales
        clientes_data = [
            {"full_name": "Juan Antonio De Los Santos", "email": "juan.santos@gmail.com", "phone": "809-555-0101", "gender": "M"},
            {"full_name": "Carlos Manuel Gómez", "email": "carlos.gomez@gmail.com", "phone": "809-555-0102", "gender": "M"},
            {"full_name": "Roberto Almonte", "email": "roberto.almonte@gmail.com", "phone": "809-555-0103", "gender": "M"},
            {"full_name": "Lisandro Rodríguez", "email": "lisandro.r@gmail.com", "phone": "809-555-0104", "gender": "M"},
            {"full_name": "David Peralta", "email": "david.peralta@gmail.com", "phone": "809-555-0105", "gender": "M"},
            {"full_name": "Fernando Fernández", "email": "fernando.f@gmail.com", "phone": "809-555-0106", "gender": "M"},
        ]

        for c_data in clientes_data:
            Client.objects.get_or_create(
                tenant=tenant,
                full_name=c_data["full_name"],
                defaults={
                    "email": c_data["email"],
                    "phone": c_data["phone"],
                    "gender": c_data["gender"]
                }
            )

        # 2. Categorías de Servicio y Servicios con Imágenes y Captions
        cat_corte, _ = ServiceCategory.objects.get_or_create(tenant=tenant, name="Cortes & Estilos", defaults={"description": "Cortes clásicos y modernos"})
        cat_barba, _ = ServiceCategory.objects.get_or_create(tenant=tenant, name="Barbería & Afeitado", defaults={"description": "Cuidado ritual de barba y piel"})
        cat_facial, _ = ServiceCategory.objects.get_or_create(tenant=tenant, name="Tratamientos Faciales", defaults={"description": "Mascarillas y limpieza profunda"})

        servicios_data = [
            {
                "name": "Corte Ejecutivo & Ritual Barba",
                "price": 1200.00,
                "duration": 45,
                "description": "Corte personalizado con lavado, perfilado de barba con navaja tradicional y toalla caliente aromática.",
                "image": "https://images.unsplash.com/photo-1503951914875-452162b0f3f1?auto=format&fit=crop&w=600&q=80",
                "categories": [cat_corte, cat_barba]
            },
            {
                "name": "Corte Básico de la Casa",
                "price": 800.00,
                "duration": 30,
                "description": "Corte moderno o clásico según preferencia con peinado final y producto fijador.",
                "image": "https://images.unsplash.com/photo-1622286342621-4bd786c2447c?auto=format&fit=crop&w=600&q=80",
                "categories": [cat_corte]
            },
            {
                "name": "Perfilado de Barba & Toalla Caliente",
                "price": 500.00,
                "duration": 25,
                "description": "Alineación de contornos con navaja, vaporizador ozono y bálsamo hidratante premium.",
                "image": "https://images.unsplash.com/photo-1621605815971-fbc98d665033?auto=format&fit=crop&w=600&q=80",
                "categories": [cat_barba]
            },
            {
                "name": "Tinte de Barba & Canas Premium",
                "price": 750.00,
                "duration": 35,
                "description": "Pigmentación orgánica natural para homogeneizar el tono de la barba sin irritar la piel.",
                "image": "https://images.unsplash.com/photo-1599351431202-1e0f0137899a?auto=format&fit=crop&w=600&q=80",
                "categories": [cat_barba]
            },
            {
                "name": "Limpieza Facial Profunda & Carbón",
                "price": 950.00,
                "duration": 40,
                "description": "Exfoliación con mascarilla de carbón activado, eliminación de puntos negros y tónico refrescante.",
                "image": "https://images.unsplash.com/photo-1512290900676-26c2a5d2938e?auto=format&fit=crop&w=600&q=80",
                "categories": [cat_facial]
            },
            {
                "name": "Tratamiento Capilar Anticaída",
                "price": 1500.00,
                "duration": 50,
                "description": "Terapia de ampollas fortalecedoras con masaje capilar estimulante del folículo piloso.",
                "image": "https://images.unsplash.com/photo-1519699047748-de8e457a634e?auto=format&fit=crop&w=600&q=80",
                "categories": [cat_corte]
            }
        ]

        for s_data in servicios_data:
            s_obj, created = Service.objects.get_or_create(
                tenant=tenant,
                name=s_data["name"],
                defaults={
                    "price": s_data["price"],
                    "duration": s_data["duration"],
                    "description": s_data["description"],
                    "image": s_data["image"]
                }
            )
            if not created:
                s_obj.price = s_data["price"]
                s_obj.description = s_data["description"]
                s_obj.image = s_data["image"]
                s_obj.save()
            s_obj.categories.set(s_data["categories"])

        # 3. Categorías de Productos y Productos con Imágenes y Captions
        prod_cat_cera, _ = ProductCategory.objects.get_or_create(tenant=tenant, name="Ceras & Pomadas")
        prod_cat_aceite, _ = ProductCategory.objects.get_or_create(tenant=tenant, name="Aceites & Bálsamos")
        prod_cat_champu, _ = ProductCategory.objects.get_or_create(tenant=tenant, name="Higiene Capilar")

        productos_data = [
            {
                "name": "Cera Mate Texturizadora Suavecito 113g",
                "sku": "PROD-CER-001",
                "price": 950.00,
                "stock": 25,
                "description": "Fijación fuerte de acabado mate natural sin residuos grasos. Ideal para peinados estructurados.",
                "image": "https://images.unsplash.com/photo-1522337360788-8b13dee7a37e?auto=format&fit=crop&w=600&q=80",
                "category": prod_cat_cera
            },
            {
                "name": "Aceite de Argán & Jojoba para Barba 50ml",
                "sku": "PROD-OIL-002",
                "price": 1100.00,
                "stock": 18,
                "description": "Nutrición intensa que suaviza el vello facial, elimina la picazón y aporta brillo saludable.",
                "image": "https://images.unsplash.com/photo-1608248597261-e4d353609802?auto=format&fit=crop&w=600&q=80",
                "category": prod_cat_aceite
            },
            {
                "name": "Champú Energizante Menta & Eucalipto 500ml",
                "sku": "PROD-SHM-003",
                "price": 1350.00,
                "stock": 30,
                "description": "Fórmula purificante que estimula el cuero cabelludo dejando una sensación refrescante de limpieza.",
                "image": "https://images.unsplash.com/photo-1535585209827-a15fcdbc4c2d?auto=format&fit=crop&w=600&q=80",
                "category": prod_cat_champu
            },
            {
                "name": "Bálsamo Hidratante Post-Afeitado 150ml",
                "sku": "PROD-BAL-004",
                "price": 850.00,
                "stock": 20,
                "description": "Calma la irritación y rojez inmediatamente después del afeitado con extracto de Aloe Vera.",
                "image": "https://images.unsplash.com/photo-1617897903246-719242758050?auto=format&fit=crop&w=600&q=80",
                "category": prod_cat_aceite
            },
            {
                "name": "Minoxidil 5% Tónico Crecimiento Capilar 60ml",
                "sku": "PROD-MNX-005",
                "price": 1800.00,
                "stock": 15,
                "description": "Tratamiento clínicamente probado para densificar la barba y combatir la pérdida folicular.",
                "image": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?auto=format&fit=crop&w=600&q=80",
                "category": prod_cat_aceite
            },
            {
                "name": "Gel Fijador Extra Fuerte Barber Pro 1kg",
                "sku": "PROD-GEL-006",
                "price": 650.00,
                "stock": 40,
                "description": "Máxima fijación de larga duración que resiste la humedad sin crear escamas blancas.",
                "image": "https://images.unsplash.com/photo-1598440947619-2c35fc9aa908?auto=format&fit=crop&w=600&q=80",
                "category": prod_cat_cera
            }
        ]

        for p_data in productos_data:
            p_obj, created = Product.objects.get_or_create(
                tenant=tenant,
                sku=p_data["sku"],
                defaults={
                    "name": p_data["name"],
                    "price": p_data["price"],
                    "stock": p_data["stock"],
                    "description": p_data["description"],
                    "image": p_data["image"],
                    "category": p_data["category"]
                }
            )
            if not created:
                p_obj.name = p_data["name"]
                p_obj.price = p_data["price"]
                p_obj.stock = p_data["stock"]
                p_obj.description = p_data["description"]
                p_obj.image = p_data["image"]
                p_obj.category = p_data["category"]
                p_obj.save()

        self.stdout.write(self.style.SUCCESS("¡Éxito! Datos demo para POS poblados correctamente con clientes, servicios y productos con imágenes y descripciones."))
