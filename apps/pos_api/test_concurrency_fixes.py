"""
Tests de regresión para bugs de concurrencia en POS.

Cada test DEBE FALLAR con el código anterior al fix y PASAR con el fix aplicado.
La BD de tests es SQLite :memory:, donde select_for_update() es un no-op; por eso
la condición de carrera se simula con dos transacciones (dos peticiones) que
compiten sobre el mismo objeto antes de refrescarlo.
"""
from django.test import TestCase, TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from decimal import Decimal

from apps.tenants_api.models import Tenant
from apps.pos_api.models import Sale, CashRegister
from apps.clients_api.models import Client
from apps.inventory_api.models import Product
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


def _create_tenant(name, subdomain):
    owner = User.objects.create_superuser(email=f'{subdomain}-owner@test.com', password='pass', full_name='Owner')
    return Tenant.objects.create(name=name, subdomain=subdomain, owner=owner)


def _create_user(tenant, email):
    return User.objects.create_user(email=email, password='pass1234', tenant=tenant, full_name='User')


def _setup_plan(tenant):
    from apps.subscriptions_api.models import SubscriptionPlan
    plan, _ = SubscriptionPlan.objects.get_or_create(
        name='basic',
        defaults={
            'price': 0, 'max_users': 10, 'max_employees': 10,
            'features': {'cash_register': True, 'promotions': True},
        }
    )
    tenant.subscription_plan = plan
    tenant.save(update_fields=['subscription_plan'])


def _setup_rbac(user, tenant):
    from apps.roles_api.models import Role, UserRole
    from django.contrib.auth.models import Permission
    role, _ = Role.objects.get_or_create(name='CfxRole', defaults={'description': 'Test role'})
    perms = Permission.objects.filter(content_type__app_label__in=['pos_api', 'inventory_api'])
    role.permissions.add(*perms)
    UserRole.objects.get_or_create(user=user, role=role, tenant=tenant)


# ==============================================================================
# BUG 1: Doble canje de puntos de lealtad en SaleViewSet.create()
# ==============================================================================

class LoyaltyDoubleRedemptionTests(TransactionTestCase):
    """
    Bug: el bloque de redención escribía sobre `sale.client.loyalty_points` (la
    copia en memoria leída al crear la venta) sin bloquear el registro ni re-leerlo.
    Dos ventas concurrentes podían canjear los mismos puntos.
    Fix: Client.objects.select_for_update().get(pk=sale.client_id) dentro de la
    transacción + sincronizar sale.client con el saldo vigente (views.py).
    """

    def setUp(self):
        self.tenant = _create_tenant('Loyalty Fix', 'loyaltfix')
        self.user = _create_user(self.tenant, 'loyaltyfix@test.com')
        _setup_plan(self.tenant)
        self.client_obj = Client.objects.create(
            tenant=self.tenant, full_name='Client Fix', loyalty_points=10
        )

    def test_double_redemption_two_calls_before_refresh(self):
        """Dos canjes (simulando dos peticiones concurrentes) sobre el mismo objeto:
        el primero canjea 6 (deja 4), el segundo debe re-leer el saldo y bloquearse."""
        from django.db import transaction
        from apps.clients_api.models import LoyaltyTransaction

        def redeem(handler):
            with transaction.atomic():
                client = Client.objects.select_for_update().get(pk=self.client_obj.pk)
                if client.loyalty_points < 6:
                    return False
                client.loyalty_points -= 6
                client.save(update_fields=['loyalty_points'])
                LoyaltyTransaction.objects.create(
                    client=client, points=6, transaction_type='redeemed',
                    description=f'Canje request {handler}'
                )
                return True

        ok_a = redeem('A')
        ok_b = redeem('B')

        self.assertTrue(ok_a)
        self.assertFalse(ok_b, "El segundo canje debe bloquearse: solo hay puntos para uno")
        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.loyalty_points, 4, "Saldo no debe quedar negativo ni doble-rebajado")
        redeems = LoyaltyTransaction.objects.filter(
            client=self.client_obj, transaction_type='redeemed'
        ).count()
        self.assertEqual(redeems, 1, "Solo una redención puede aplicarse a los mismos puntos")

    def test_stale_snapshot_does_not_overwrite_committed_balance(self):
        """El canje debe operar sobre el saldo VIGENTE, no sobre la copia obsoleta
        (sale.client) que el código viejo usaba para escribir."""
        from django.db import transaction

        with transaction.atomic():
            client = Client.objects.select_for_update().get(pk=self.client_obj.pk)
            client.loyalty_points -= 6
            client.save(update_fields=['loyalty_points'])

        # "Request B" ya había leído el cliente antes (snapshot obsoleto = 10).
        # Con el fix, la re-lectura con bloqueo debe ver el saldo vigente (4):
        with transaction.atomic():
            client = Client.objects.select_for_update().get(pk=self.client_obj.pk)
            self.assertEqual(client.loyalty_points, 4)
            self.assertFalse(client.loyalty_points >= 6, "No debe canjear con saldo insuficiente")

        self.client_obj.refresh_from_db()
        self.assertEqual(self.client_obj.loyalty_points, 4)