from django.core.management.base import BaseCommand
from apps.subscriptions_api.models import SubscriptionPlan
from decimal import Decimal


DEFAULT_PLANS = [
    {
        "name": "basic",
        "description": "Plan básico para barberías individuales",
        "price": Decimal("29.99"),
        "annual_price": Decimal("299.99"),
        "max_employees": 3,
        "max_users": 5,
        "allows_multiple_branches": False,
        "features": {
            "cash_register": True,
            "appointments": True,
            "inventory": True,
            "reports": True,
            "basic_reports": True,
            "client_history": True,
            "promotions": False,
            "multi_location": False,
            "advanced_reports": False,
            "payroll": False,
            "custom_branding": False,
            "whatsapp_notifications": False,
            "export_reports": False,
            "priority_support": False,
        },
        "commercial_benefits": [
            "1 Sucursal Principal",
            "Hasta 3 Empleados",
            "Punto de Venta (POS) y Caja Diaria",
            "Agenda de Citas en Tiempo Real",
            "Inventario de Productos",
            "Reportes Básicos",
            "Soporte por Correo",
        ],
        "is_active": True,
    },
    {
        "name": "standard",
        "description": "Plan Pro para negocios en crecimiento",
        "price": Decimal("59.99"),
        "annual_price": Decimal("599.99"),
        "max_employees": 10,
        "max_users": 15,
        "allows_multiple_branches": True,
        "features": {
            "cash_register": True,
            "appointments": True,
            "inventory": True,
            "reports": True,
            "basic_reports": True,
            "client_history": True,
            "promotions": True,
            "multi_location": True,
            "advanced_reports": True,
            "payroll": True,
            "custom_branding": False,
            "whatsapp_notifications": False,
            "export_reports": False,
            "priority_support": False,
        },
        "commercial_benefits": [
            "Hasta 3 Sucursales",
            "Hasta 10 Empleados y 15 Usuarios",
            "Promociones y Cupones",
            "Reportes Avanzados y BI",
            "Comisiones y Nómina TSS",
            "Soporte Prioritario por Correo",
        ],
        "is_active": True,
    },
    {
        "name": "premium",
        "description": "Plan Business para spas y salones consolidados",
        "price": Decimal("99.99"),
        "annual_price": Decimal("999.99"),
        "max_employees": 25,
        "max_users": 30,
        "allows_multiple_branches": True,
        "features": {
            "cash_register": True,
            "appointments": True,
            "inventory": True,
            "reports": True,
            "basic_reports": True,
            "client_history": True,
            "promotions": True,
            "multi_location": True,
            "advanced_reports": True,
            "payroll": True,
            "custom_branding": True,
            "whatsapp_notifications": True,
            "export_reports": False,
            "priority_support": False,
        },
        "commercial_benefits": [
            "Todo lo del Plan Pro",
            "Sucursales Ilimitadas",
            "Hasta 25 Empleados y 30 Usuarios",
            "Conexión WhatsApp mediante QR",
            "Branding Personalizado (Logo y Colores)",
            "Soporte Prioritario por Correo y WhatsApp",
        ],
        "is_active": True,
    },
    {
        "name": "enterprise",
        "description": "Plan Enterprise ilimitado para cadenas y franquicias",
        "price": Decimal("199.99"),
        "annual_price": Decimal("1999.99"),
        "max_employees": 0,
        "max_users": 0,
        "allows_multiple_branches": True,
        "features": {
            "cash_register": True,
            "appointments": True,
            "inventory": True,
            "reports": True,
            "basic_reports": True,
            "client_history": True,
            "promotions": True,
            "multi_location": True,
            "advanced_reports": True,
            "payroll": True,
            "custom_branding": True,
            "whatsapp_notifications": True,
            "export_reports": True,
            "priority_support": True,
        },
        "commercial_benefits": [
            "Todo lo del Plan Business",
            "Empleados Ilimitados",
            "Exportación Excel de Reportes",
            "Auditoría Avanzada",
            "Soporte Dedicado con Seguimiento Personalizado",
        ],
        "is_active": True,
    },
]


class Command(BaseCommand):
    help = "Sincroniza planes de suscripción (idempotente). Fuente de verdad única."

    def handle(self, *args, **options):
        for p_data in DEFAULT_PLANS:
            plan, created = SubscriptionPlan.objects.update_or_create(
                name=p_data["name"],
                defaults=p_data,
            )
            action = "CREADO" if created else "ACTUALIZADO"
            self.stdout.write(
                f"  [PLAN] {action}: {plan.get_name_display()} "
                f"features: {plan.features}"
            )

        self.stdout.write(self.style.SUCCESS("Planes sincronizados correctamente"))
