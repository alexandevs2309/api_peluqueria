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
        "features": {"pos": True, "appointments": True, "inventory": True},
    },
    {
        "name": "standard",
        "description": "Plan Pro para negocios en crecimiento",
        "price": Decimal("59.99"),
        "annual_price": Decimal("599.99"),
        "max_employees": 10,
        "max_users": 15,
        "allows_multiple_branches": True,
        "features": {"pos": True, "appointments": True, "inventory": True, "multi_branch": True, "promotions": True, "reports_advanced": True},
    },
    {
        "name": "premium",
        "description": "Plan Business para spas y salones consolidados",
        "price": Decimal("99.99"),
        "annual_price": Decimal("999.99"),
        "max_employees": 25,
        "max_users": 30,
        "allows_multiple_branches": True,
        "features": {"pos": True, "appointments": True, "inventory": True, "multi_branch": True, "reports_advanced": True, "promotions": True, "custom_branding": True},
    },
    {
        "name": "enterprise",
        "description": "Plan Enterprise ilimitado para cadenas y franquicias",
        "price": Decimal("199.99"),
        "annual_price": Decimal("1999.99"),
        "max_employees": 0,
        "max_users": 0,
        "allows_multiple_branches": True,
        "features": {"pos": True, "appointments": True, "inventory": True, "multi_branch": True, "api_access": True, "promotions": True, "reports_advanced": True, "custom_branding": True},
    },
]


class Command(BaseCommand):
    help = "Sincroniza planes de suscripción (idempotente)"

    def handle(self, *args, **options):
        for p_data in DEFAULT_PLANS:
            plan, created = SubscriptionPlan.objects.update_or_create(
                name=p_data["name"],
                defaults=p_data,
            )
            action = "CREADO" if created else "ACTUALIZADO"
            self.stdout.write(f"  [PLAN] {action}: {plan.get_name_display()} - features: {plan.features}")

        self.stdout.write(self.style.SUCCESS("✅ Planes sincronizados correctamente"))