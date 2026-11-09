from decimal import Decimal
from datetime import date
import pytest
from django.test import TestCase
from apps.tenants_api.models import Tenant
from apps.auth_api.models import User
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Liquidacion
from apps.subscriptions_api.models import SubscriptionPlan


@pytest.mark.django_db
class TestLiquidacion(TestCase):
    def setUp(self):
        plan = SubscriptionPlan.objects.create(name='basic', price=10, is_active=True, is_public=True)
        self.tenant = Tenant.objects.create(name='T', subdomain='tl', subscription_plan=plan, is_active=True)
        self.admin = User.objects.create_user(email='admin@t.com', password='p', full_name='Admin', tenant=self.tenant, is_email_verified=True)
        from apps.auth_api.models import User as U
        self.emp_user = U.objects.create_user(email='emp@t.com', password='p', full_name='Emp', tenant=self.tenant, is_email_verified=True)
        self.emp = Employee.objects.create(user=self.emp_user, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('50000.00'), is_active=True, hire_date=date(2020,1,1))

    def test_desahucio_full_prestaciones(self):
        liq = Liquidacion.calculate(employee=self.emp, termination_date=date(2026,6,15), termination_type='desahucio')
        assert liq.preaviso_days == 28
        assert liq.cesantia_days > 0
        assert liq.total > 0
        assert liq.termination_type == 'desahucio'

    def test_despido_con_causa_no_prestaciones(self):
        liq = Liquidacion.calculate(employee=self.emp, termination_date=date(2026,6,15), termination_type='despido_causa')
        assert liq.preaviso_days == 0
        assert liq.cesantia_days == 0
        # vacation + regalia may be > 0
        assert liq.total >= 0

    def test_dimision_sin_causa_no_prestaciones(self):
        liq = Liquidacion.calculate(employee=self.emp, termination_date=date(2026,6,15), termination_type='dimision_sin_causa')
        assert liq.preaviso_days == 0
        assert liq.cesantia_days == 0

    def test_dimision_con_causa_full(self):
        liq = Liquidacion.calculate(employee=self.emp, termination_date=date(2026,6,15), termination_type='dimision_causa')
        assert liq.preaviso_days == 28
        assert liq.cesantia_days > 0

    def test_mutuo_acuerdo_no_auto_prestaciones(self):
        liq = Liquidacion.calculate(employee=self.emp, termination_date=date(2026,6,15), termination_type='mutuo_acuerdo')
        # Mutuo acuerdo: preaviso y cesantía no se asignan automáticamente (son pactados)
        assert liq.preaviso_days == 0
        assert liq.cesantia_days == 0

    def test_cesantia_tramos(self):
        from apps.auth_api.models import User as U
        u = U.objects.create_user(email='emp2@t.com', password='p', full_name='Emp2', tenant=self.tenant, is_email_verified=True)
        emp4 = Employee.objects.create(user=u, tenant=self.tenant, payment_type='fixed', fixed_salary=Decimal('50000.00'), is_active=True, hire_date=date(2026,2,15))
        liq = Liquidacion.calculate(employee=emp4, termination_date=date(2026,6,15), termination_type='desahucio')
        assert liq.cesantia_days == Decimal('6')

    def test_participacion_beneficios_tope(self):
        liq = Liquidacion.calculate(employee=self.emp, termination_date=date(2026,6,15), termination_type='desahucio', total_utilities=1000000, total_payroll=500000)
        assert liq.participacion_beneficios > 0
        # tope 60 días (>=3 años? emp hired 2020 → 6 years → 60 days)
        daily = Decimal('50000.00') / Decimal('23.83')
        cap = (daily * 60).quantize(Decimal('0.01'))
        assert liq.participacion_beneficios <= cap

    def test_liquidacion_idempotent(self):
        l1 = Liquidacion.calculate(employee=self.emp, termination_date=date(2026,6,15), termination_type='desahucio')
        l2 = Liquidacion.calculate(employee=self.emp, termination_date=date(2026,6,15), termination_type='desahucio')
        assert l1.id == l2.id  # idempotent: no duplicate

    def test_asistencia_economica_included(self):
        liq = Liquidacion.calculate(employee=self.emp, termination_date=date(2026,6,15), termination_type='desahucio', asistencia_economica=Decimal('5000.00'))
        assert liq.asistencia_economica == Decimal('5000.00')
        assert liq.total >= Decimal('5000.00')

    def test_participacion_exempt(self):
        liq = Liquidacion.calculate(employee=self.emp, termination_date=date(2026,6,15), termination_type='desahucio', total_utilities=1000000, total_payroll=500000, participacion_exempt=True)
        assert liq.participacion_beneficios == Decimal('0.00')
        from apps.tenants_api.models import Tenant
        plan2 = SubscriptionPlan.objects.create(name='basic2', price=10, is_active=True, is_public=True)
        t2 = Tenant.objects.create(name='T2', subdomain='tl2', subscription_plan=plan2, is_active=True)
        from apps.auth_api.models import User as U
        u2 = U.objects.create_user(email='e2@t.com', password='p', full_name='E2', tenant=t2, is_email_verified=True)
        emp2 = Employee.objects.create(user=u2, tenant=t2, payment_type='fixed', fixed_salary=Decimal('50000.00'), is_active=True, hire_date=date(2020,1,1))
        liq = Liquidacion.calculate(employee=emp2, termination_date=date(2026,6,15), termination_type='desahucio')
        assert liq.tenant_id == t2.id