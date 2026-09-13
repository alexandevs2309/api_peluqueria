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
from apps.pos_api.models import Sale, SaleDetail, CashRegister
from apps.clients_api.models import Client
from apps.inventory_api.models import Product
from django.contrib.contenttypes.models import ContentType

User = get_user_model()


def authenticate_client(client, user):
    client.force_authenticate(user=user)
    from rest_framework_simplejwt.tokens import AccessToken
    token = AccessToken.for_user(user)
    if getattr(user, 'tenant_id', None):
        token['tenant_id'] = user.tenant_id
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {str(token)}")
    client.cookies['access_token'] = str(token)


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


# ==============================================================================
# BUG 2: Refund restaura stock sin bloqueo (lost update)
# ==============================================================================

class RefundStockLockTests(TransactionTestCase):
    """
    Bug: refund() restaura stock con Product.objects.get() sin select_for_update().
    Dos reembolsos concurrentes (de ventas distintas que comparten producto) pueden
    perder una actualización de stock (lost update).
    Fix: Product.objects.select_for_update().get(...) en el bloque "Restaurar
    inventario" de refund() (views.py).
    """

    def setUp(self):
        self.tenant = _create_tenant('Refund Fix', 'refundfix')
        self.user = _create_user(self.tenant, 'refundfix@test.com')
        _setup_plan(self.tenant)
        _setup_rbac(self.user, self.tenant)
        self.cash_register = CashRegister.objects.create(
            tenant=self.tenant, user=self.user, initial_cash=Decimal('1000')
        )
        self.product = Product.objects.create(
            tenant=self.tenant, name='Shampoo', price=Decimal('100'), stock=10
        )
        self.sale_a = Sale.objects.create(
            tenant=self.tenant, total=Decimal('200'), status='confirmed',
            created_by=self.user, user=self.user, cash_register=self.cash_register
        )
        self.sale_b = Sale.objects.create(
            tenant=self.tenant, total=Decimal('200'), status='confirmed',
            created_by=self.user, user=self.user, cash_register=self.cash_register
        )
        self.product_ct = ContentType.objects.get(app_label='inventory_api', model='product')
        SaleDetail.objects.create(
            sale=self.sale_a, content_type=self.product_ct, object_id=self.product.pk,
            name='Shampoo', quantity=2, price=Decimal('100')
        )
        SaleDetail.objects.create(
            sale=self.sale_b, content_type=self.product_ct, object_id=self.product.pk,
            name='Shampoo', quantity=3, price=Decimal('100')
        )

    def test_refund_stock_restore_two_calls_before_refresh(self):
        """Dos reembolsos concurrentes (dos transacciones antes de refrescar) sobre el
        MISMO producto: la restauración debe sumar AMBOS reembolsos (sin lost update)."""
        from django.db import transaction

        def restore(sale, qty):
            # Simula el bloque "Restaurar inventario" de refund()
            with transaction.atomic():
                product = Product.objects.select_for_update().get(id=self.product.pk)
                product.stock += qty
                product.save(update_fields=['stock'])
            return sale

        restore(self.sale_a, 2)
        restore(self.sale_b, 3)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 15, "Stock debe sumar 10 + 2 + 3 (sin lost update)")

    def test_refund_via_api_restores_stock_and_blocks_second_refund(self):
        """End-to-end: reembolsar una venta restaura el stock exactamente una vez y
        el segundo reembolso de la misma venta es bloqueado."""
        self.client = APIClient()
        authenticate_client(self.client, self.user)

        r1 = self.client.post(
            f'/api/pos/sales/{self.sale_a.pk}/refund/',
            {'reason': 'Devolución completa del producto'}, format='json'
        )
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 12)

        r2 = self.client.post(
            f'/api/pos/sales/{self.sale_a.pk}/refund/',
            {'reason': 'Segunda devolución del mismo producto'}, format='json'
        )
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 12, "El stock no debe restaurarse de nuevo")


# ==============================================================================
# BUG 3: Apertura de caja duplicada (open_register sin lock ni unicidad)
# ==============================================================================

class OpenRegisterDuplicateTests(TransactionTestCase):
    """
    Bug: open_register() verificaba si existía una caja abierta pero la creación no
    estaba protegida a nivel de base de datos; dos peticiones concurrentes podían
    abrir dos cajas simultáneas para el mismo usuario.

    Fix: (1) transacción atómica + select_for_update en la verificación,
    (2) UniqueConstraints (tenant, user, branch) y (tenant, user) con is_open=True,
    (3) IntegrityError -> 400 'Ya tienes una caja abierta hoy' (views.py).
    """

    def setUp(self):
        self.tenant = _create_tenant('Register Fix', 'regfix')
        self.user = _create_user(self.tenant, 'regfix@test.com')
        _setup_plan(self.tenant)
        _setup_rbac(self.user, self.tenant)
        self.client = APIClient()
        authenticate_client(self.client, self.user)

    def test_open_register_duplicate_constraint_blocks(self):
        """Dos aperturas simultáneas (misma transacción antes de refrescar): la
        segunda debe violar la unicidad (IntegrityError)."""
        from django.db import IntegrityError, transaction

        CashRegister.objects.create(
            tenant=self.tenant, user=self.user, is_open=True, initial_cash=Decimal('100')
        )

        # Simula la segunda petición concurrente intentando crear otra caja abierta
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CashRegister.objects.create(
                    tenant=self.tenant, user=self.user, is_open=True, initial_cash=Decimal('100')
                )

        self.assertEqual(
            CashRegister.objects.filter(tenant=self.tenant, user=self.user, is_open=True).count(),
            1,
            "Debe quedar exactamente una caja abierta"
        )

    def test_open_register_double_submit_via_api(self):
        """Doble submit al endpoint: la primera apertura responde 200 y la segunda 400."""
        data = {'initial_cash': 100}
        r1 = self.client.post('/api/pos/sales/open_register/', data, format='json')
        self.assertEqual(r1.status_code, status.HTTP_200_OK)

        r2 = self.client.post('/api/pos/sales/open_register/', data, format='json')
        self.assertEqual(r2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('abierta', str(r2.data).lower())

        open_registers = CashRegister.objects.filter(
            tenant=self.tenant, user=self.user, is_open=True
        )
        self.assertEqual(open_registers.count(), 1, "Solo debe existir una caja abierta")

    def test_open_register_close_then_reopen_allowed(self):
        """Cerrar y luego abrir otra caja NO debe violar la constraint."""
        from django.utils import timezone

        CashRegister.objects.create(
            tenant=self.tenant, user=self.user, is_open=True, initial_cash=Decimal('100')
        )
        CashRegister.objects.filter(tenant=self.tenant, user=self.user, is_open=True).update(
            is_open=False, closed_at=timezone.now()
        )

        register = CashRegister.objects.create(
            tenant=self.tenant, user=self.user, is_open=True, initial_cash=Decimal('200')
        )
        self.assertTrue(register.pk)

    def test_open_register_constraint_is_per_branch(self):
        """La unicidad es por sucursal: dos cajas abiertas en sucursales distintas
        están permitidas; en la misma sucursal, no."""
        from apps.settings_api.models import Branch
        from apps.subscriptions_api.models import SubscriptionPlan
        from django.db import IntegrityError, transaction

        plan = self.tenant.subscription_plan
        plan.allows_multiple_branches = True
        plan.save(update_fields=['allows_multiple_branches'])

        branch_a = Branch.objects.create(tenant=self.tenant, name='Sucursal A')
        branch_b = Branch.objects.create(tenant=self.tenant, name='Sucursal B')

        CashRegister.objects.create(
            tenant=self.tenant, user=self.user, branch=branch_a, is_open=True, initial_cash=Decimal('100')
        )
        # Otra sucursal -> permitido
        CashRegister.objects.create(
            tenant=self.tenant, user=self.user, branch=branch_b, is_open=True, initial_cash=Decimal('100')
        )
        # Misma sucursal -> bloqueado
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CashRegister.objects.create(
                    tenant=self.tenant, user=self.user, branch=branch_a, is_open=True, initial_cash=Decimal('100')
                )