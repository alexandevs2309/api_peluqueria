"""
Regresión BE-05 / BE-07: reembolso con tenant correcto e idempotencia real.

BE-05: un SuperAdmin tiene `request.tenant = None` (TenantMiddleware). El
reembolso debe devolver el stock al producto del tenant DE LA VENTA, no al
producto filtrado por `request.tenant`.

BE-07: un reembolso PARCIAL no cierra la venta. Si no hay componentes de
comisión, la clave de idempotencia no se persiste en ningún lado y un reintento
duplica la reposición de stock y el `amount_refunded`.
"""
import pytest
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TransactionTestCase
from rest_framework import status
from rest_framework.test import APIClient

from apps.tenants_api.models import Tenant
from apps.pos_api.models import Sale, SaleDetail, CashRegister
from apps.inventory_api.models import Product, StockMovement

User = get_user_model()


class RefundTenantIdempotencyTests(TransactionTestCase):
    def setUp(self):
        self.plan_user = User.objects.create_superuser(
            email='refund-super@test.com', password='pass', full_name='Super'
        )
        self.tenant = Tenant.objects.create(
            name='Refund Tenant', subdomain='refundtenant', owner=self.plan_user
        )
        from apps.subscriptions_api.models import SubscriptionPlan
        plan, _ = SubscriptionPlan.objects.get_or_create(
            name='basic',
            defaults={'price': 0, 'features': {'cash_register': True, 'promotions': True}},
        )
        plan.features = {'cash_register': True, 'promotions': True}
        plan.save(update_fields=['features'])
        self.tenant.subscription_plan = plan
        self.tenant.save(update_fields=['subscription_plan'])

        self.user = User.objects.create_user(
            email='refund-user@test.com', password='pass', tenant=self.tenant, full_name='User'
        )
        from django.contrib.auth.models import Permission
        from apps.roles_api.models import Role, UserRole
        role, _ = Role.objects.get_or_create(name='RefundRole', defaults={'description': 'Test'})
        role.permissions.add(*Permission.objects.filter(
            content_type__app_label__in=['pos_api', 'inventory_api']
        ))
        UserRole.objects.get_or_create(user=self.user, role=role, tenant=self.tenant)
        self.cash = CashRegister.objects.create(
            tenant=self.tenant, user=self.user, initial_cash=Decimal('1000')
        )
        self.product = Product.objects.create(
            tenant=self.tenant, name='Shampoo', price=Decimal('100'), stock=10
        )
        self.sale = Sale.objects.create(
            tenant=self.tenant, total=Decimal('200'), status='confirmed',
            user=self.user, created_by=self.user, cash_register=self.cash,
        )
        self.product_ct = ContentType.objects.get(app_label='inventory_api', model='product')
        SaleDetail.objects.create(
            sale=self.sale, content_type=self.product_ct, object_id=self.product.pk,
            name='Shampoo', quantity=2, price=Decimal('100'),
        )

    def _client(self, user):
        from rest_framework_simplejwt.tokens import AccessToken
        client = APIClient()
        client.force_authenticate(user=user)
        token = AccessToken.for_user(user)
        if getattr(user, 'tenant_id', None):
            token['tenant_id'] = user.tenant_id
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {str(token)}')
        client.cookies['access_token'] = str(token)
        return client

    # ── BE-05 ────────────────────────────────────────────────────────────────
    def test_superadmin_refund_restores_stock_in_sale_tenant(self):
        """T3: SuperAdmin (request.tenant=None) reembolsa venta ajena."""
        client = self._client(self.plan_user)
        response = client.post(
            f'/api/pos/sales/{self.sale.pk}/refund/',
            {'reason': 'Devolución completa por error del cliente'},
            format='json',
        )
        assert response.status_code == status.HTTP_200_OK, response.data
        self.product.refresh_from_db()
        assert self.product.stock == 12, 'El stock de la venta debe reponerse aunque el admin no tenga tenant'
        assert StockMovement.objects.filter(product=self.product, quantity=2).exists()

    # ── BE-07 ────────────────────────────────────────────────────────────────
    def test_partial_refund_replay_without_components_is_idempotent(self):
        """Sin comisiones, la clave debe persistirse igualmente y bloquear el replay."""
        client = self._client(self.user)
        payload = {
            'reason': 'Devolución parcial por producto defectuoso',
            'amount': '100.00',
            'idempotency_key': 'refund-be07-key',
        }
        first = client.post(f'/api/pos/sales/{self.sale.pk}/refund/', payload, format='json')
        assert first.status_code == status.HTTP_200_OK, first.data

        self.product.refresh_from_db()
        assert self.product.stock == 11

        second = client.post(f'/api/pos/sales/{self.sale.pk}/refund/', payload, format='json')
        assert second.status_code == status.HTTP_200_OK
        assert second.data.get('idempotent') is True, 'El replay debe declararse idempotente'

        self.product.refresh_from_db()
        self.sale.refresh_from_db()
        assert self.product.stock == 11, 'El replay no debe reponer stock dos veces'
        assert self.sale.amount_refunded == Decimal('100.00'), 'El replay no debe duplicar amount_refunded'
