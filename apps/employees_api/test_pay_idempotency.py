"""
Regresión BE-01: pago único de regalía pascual y liquidación.

Criterio de cierre: dos peticiones que lean el estado `calculated` no deben
producir dos pagos. La transición a `paid` debe ser condicional y atómica;
la segunda intentativa debe rechazarse sin sobrescribir paid_at/paid_by/
payment_reference.

Nota: la BD de tests es SQLite, donde `select_for_update()` es no-op. La
carrera se simula cargando dos instancias "stale" que ambas vieron el estado
`calculated`, exactamente como dos peticiones concurrentes.
"""
import pytest
from decimal import Decimal
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from apps.subscriptions_api.models import SubscriptionPlan
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import RegaliaPascual, Liquidacion

User = get_user_model()


@pytest.mark.django_db
class TestPayOnceRegalia(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=10, is_active=True, is_public=True)
        self.tenant = Tenant.objects.create(name='T', subdomain='be01r', subscription_plan=plan, is_active=True)
        self.admin = User.objects.create_superuser(
            email='be01r@test.com', password='p', full_name='Admin', tenant=self.tenant
        )
        self.emp = Employee.objects.create(
            user=self.admin, tenant=self.tenant, payment_type='fixed',
            fixed_salary=Decimal('50000.00'), is_active=True,
        )
        self.regalia = RegaliaPascual.objects.create(
            employee=self.emp, tenant=self.tenant, year=2026,
            ordinary_salary_annual=Decimal('600000.00'), amount=Decimal('50000.00'),
            status='calculated',
        )

    def test_two_stale_reads_only_one_payment_wins(self):
        """Dos lecturas del estado `calculated`: sólo la primera debe pagar."""
        r1 = RegaliaPascual.objects.get(pk=self.regalia.pk)
        r2 = RegaliaPascual.objects.get(pk=self.regalia.pk)

        r1.mark_as_paid(self.admin, 'REF-1')

        with pytest.raises(Exception) as exc:
            r2.mark_as_paid(self.admin, 'REF-2')

        assert 'pagad' in str(exc.value).lower() or 'paid' in str(exc.value).lower()

        self.regalia.refresh_from_db()
        assert self.regalia.status == 'paid'
        assert self.regalia.payment_reference == 'REF-1', 'El segundo pago sobrescribió la referencia'

    def _pay_view(self, data):
        from rest_framework.request import Request
        from rest_framework.parsers import JSONParser
        from rest_framework.test import APIRequestFactory
        from apps.employees_api.earnings_views import PayrollViewSet
        raw = APIRequestFactory().post(
            f"/api/employees/client/payroll/regalia/{self.regalia.pk}/pay", data, format='json'
        )
        request = Request(raw, parsers=[JSONParser()])
        request.user = self.admin
        request.tenant = self.tenant
        return PayrollViewSet().pay_regalia(request, regalia_id=str(self.regalia.pk))

    def test_view_replay_same_key_is_idempotent(self):
        first = self._pay_view({'reference': 'REF-1', 'idempotency_key': 'key-abc'})
        assert first.status_code == 200

        self.regalia.refresh_from_db()
        paid_at = self.regalia.paid_at

        replay = self._pay_view({'reference': 'REF-1', 'idempotency_key': 'key-abc'})
        assert replay.status_code == 200, 'El reintento con la misma clave debe ser idempotente'

        self.regalia.refresh_from_db()
        assert self.regalia.paid_at == paid_at, 'El replay no debe repetir el pago'
        assert self.regalia.payment_reference == 'REF-1'

    def test_view_second_key_after_paid_returns_409(self):
        assert self._pay_view({'idempotency_key': 'key-1'}).status_code == 200
        second = self._pay_view({'idempotency_key': 'key-2'})
        assert second.status_code == 409, 'Clave distinta sobre obligación pagada debe ser 409'
        assert second.data['error'] == 'Ya fue pagada'

    def test_view_amount_is_decimal_string(self):
        response = self._pay_view({'idempotency_key': 'key-amount'})
        assert response.status_code == 200
        assert response.data['amount'] == '50000.00', 'El importe debe viajar como Decimal'

    def test_cross_tenant_regalia_is_not_payable(self):
        from rest_framework.test import APIRequestFactory
        from apps.employees_api.earnings_views import PayrollViewSet
        other_plan = SubscriptionPlan.objects.create(name='other', price=10, is_active=True, is_public=True)
        other_tenant = Tenant.objects.create(
            name='Other', subdomain='be01other', subscription_plan=other_plan, is_active=True
        )
        other_regalia = RegaliaPascual.objects.create(
            employee=self.emp, tenant=other_tenant, year=2027, amount=Decimal('100.00'), status='calculated'
        )
        request = APIRequestFactory().post('/pay', {}, format='json')
        request.user = self.admin
        request.tenant = self.tenant
        response = PayrollViewSet().pay_regalia(request, regalia_id=str(other_regalia.pk))
        assert response.status_code == 404


@pytest.mark.django_db
class TestPayOnceLiquidacion(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=10, is_active=True, is_public=True)
        self.tenant = Tenant.objects.create(name='T', subdomain='be01l', subscription_plan=plan, is_active=True)
        self.admin = User.objects.create_superuser(
            email='be01l@test.com', password='p', full_name='Admin', tenant=self.tenant
        )
        self.emp = Employee.objects.create(
            user=self.admin, tenant=self.tenant, payment_type='fixed',
            fixed_salary=Decimal('50000.00'), is_active=True,
        )
        self.liq = Liquidacion.objects.create(
            employee=self.emp, tenant=self.tenant,
            termination_date=date(2026, 6, 30), termination_type='desahucio',
            daily_salary=Decimal('2000.00'), total=Decimal('80000.00'),
            status='calculated',
        )

    def test_two_stale_reads_only_one_payment_wins(self):
        l1 = Liquidacion.objects.get(pk=self.liq.pk)
        l2 = Liquidacion.objects.get(pk=self.liq.pk)

        l1.mark_as_paid(self.admin, 'REF-1')

        with pytest.raises(Exception) as exc:
            l2.mark_as_paid(self.admin, 'REF-2')

        assert 'pagad' in str(exc.value).lower() or 'paid' in str(exc.value).lower()

        self.liq.refresh_from_db()
        assert self.liq.status == 'paid'
        assert self.liq.payment_reference == 'REF-1', 'El segundo pago sobrescribió la referencia'

    def _pay_view(self, data):
        from rest_framework.request import Request
        from rest_framework.parsers import JSONParser
        from rest_framework.test import APIRequestFactory
        from apps.employees_api.earnings_views import PayrollViewSet
        raw = APIRequestFactory().post(
            f"/api/employees/client/payroll/liquidaciones/{self.liq.pk}/pay", data, format='json'
        )
        request = Request(raw, parsers=[JSONParser()])
        request.user = self.admin
        request.tenant = self.tenant
        return PayrollViewSet().pay_liquidacion(request, liq_id=str(self.liq.pk))

    def test_view_replay_same_key_is_idempotent(self):
        assert self._pay_view({'reference': 'REF-1', 'idempotency_key': 'key-liq'}).status_code == 200
        self.liq.refresh_from_db()
        paid_at = self.liq.paid_at
        assert self._pay_view({'reference': 'REF-1', 'idempotency_key': 'key-liq'}).status_code == 200
        self.liq.refresh_from_db()
        assert self.liq.paid_at == paid_at

    def test_view_second_key_after_paid_returns_409_and_decimal(self):
        first = self._pay_view({'idempotency_key': 'key-liq-1'})
        assert first.status_code == 200
        assert first.data['total'] == '80000.00', 'El total debe viajar como Decimal'
        second = self._pay_view({'idempotency_key': 'key-liq-2'})
        assert second.status_code == 409
