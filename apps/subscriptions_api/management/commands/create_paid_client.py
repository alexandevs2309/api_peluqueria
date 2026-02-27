from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.auth_api.models import User
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription
from apps.settings_api.models import Branch, Setting
from apps.billing_api.models import Invoice
import secrets
import string

class Command(BaseCommand):
    help = 'Crear usuario Client-Admin con plan pagado'

    def add_arguments(self, parser):
        parser.add_argument('--email', type=str, required=True)
        parser.add_argument('--name', type=str, required=True)
        parser.add_argument('--business', type=str, required=True)
        parser.add_argument('--plan', type=str, default='standard', choices=['basic', 'standard', 'premium'])
        parser.add_argument('--password', type=str, default=None)

    def handle(self, *args, **options):
        email = options['email']
        name = options['name']
        business = options['business']
        plan_name = options['plan']
        password = options['password'] or self.generate_password()

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.ERROR(f'Usuario {email} ya existe'))
            return

        try:
            plan = SubscriptionPlan.objects.get(name=plan_name)
        except SubscriptionPlan.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Plan {plan_name} no existe'))
            return

        with transaction.atomic():
            # Crear usuario temporal como superuser
            user = User(
                email=email,
                full_name=name,
                is_active=True,
                is_superuser=True,
                is_staff=True,
                tenant=None,
                role=None
            )
            user.set_password(password)
            user.save(skip_validation=True)

            # Crear tenant
            subdomain = business.lower().replace(' ', '')[:20] + str(user.id)
            tenant = Tenant.objects.create(
                name=business,
                subdomain=subdomain,
                owner=user,
                contact_email=email,
                subscription_plan=plan,
                subscription_status='active',
                trial_end_date=None,
                is_active=True
            )

            # Actualizar usuario a Client-Admin
            user.is_superuser = False
            user.is_staff = False
            user.tenant = tenant
            user.role = 'Client-Admin'
            user.save(skip_validation=True)

            # Crear suscripción activa (30 días)
            user_subscription = UserSubscription.objects.create(
                user=user,
                plan=plan,
                start_date=timezone.now(),
                end_date=timezone.now() + timezone.timedelta(days=30),
                is_active=True,
                auto_renew=False
            )

            # Crear factura pagada
            Invoice.objects.create(
                user=user,
                subscription=user_subscription,
                amount=plan.price,
                description=f"{plan.get_name_display()} - Primer mes",
                due_date=timezone.now(),
                is_paid=True,
                paid_at=timezone.now(),
                payment_method='manual',
                status='paid'
            )

            # Crear sucursal principal
            branch = Branch.objects.create(
                tenant=tenant,
                name='Sucursal Principal',
                address='Dirección por defecto',
                is_main=True,
                is_active=True
            )

            # Crear configuración
            Setting.objects.create(
                branch=branch,
                business_name=tenant.name,
                business_email=tenant.contact_email,
                currency='USD',
                timezone='America/Santo_Domingo'
            )

        self.stdout.write(self.style.SUCCESS(f'\n✅ Usuario creado exitosamente:'))
        self.stdout.write(f'Email: {email}')
        self.stdout.write(f'Password: {password}')
        self.stdout.write(f'Business: {business}')
        self.stdout.write(f'Plan: {plan.get_name_display()} (${plan.price}/mes)')
        self.stdout.write(f'Status: active (30 días)')
        self.stdout.write(f'Tenant ID: {tenant.id}')

    def generate_password(self, length=12):
        characters = string.ascii_letters + string.digits + "!@#$%"
        return ''.join(secrets.choice(characters) for _ in range(length))
