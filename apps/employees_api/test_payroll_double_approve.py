"""
Tests de regresión para el bug de doble aprobación de nómina.

Bug: approve_period() leía el período con PayrollPeriod.objects.get() sin bloqueo;
dos peticiones concurrentes podían aprobar el mismo período dos veces (doble
notificación y sobrescritura de la aprobación).

Fix: select_for_update() + transaction.atomic() sobre el período; la notificación
se envía FUERA del bloque atómico (earnings_views.py).
La BD de tests es SQLite :memory:, donde select_for_update() es no-op; la condición
de carrera se simula con dos transacciones que compiten sobre el mismo objeto.
"""
import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.db import transaction

from apps.tenants_api.models import Tenant
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollPeriod
from apps.employees_api.earnings_views import PayrollViewSet
from apps.pos_api.models import Sale

User = get_user_model()


@pytest.mark.django_db
class TestPayrollDoubleApprove:
    """Doble aprobación de un período de nómina bajo condiciones de carrera."""

    @pytest.fixture
    def setup_data(self):
        owner = User.objects.create_superuser(
            email='payroll_admin@test.com', password='pass', full_name='Admin Nomina'
        )
        tenant = Tenant.objects.create(name='Payroll Fix', subdomain='payrollfix', owner=owner)
        employee_user = User.objects.create_user(
            email='payroll_emp@test.com', password='password', tenant=tenant
        )
        employee = Employee.objects.create(
            user=employee_user,
            tenant=tenant,
            payment_type='commission',
            commission_rate=Decimal('10.00'),
            fixed_salary=Decimal('0.00')
        )
        Sale.objects.create(
            employee=employee,
            tenant=tenant,
            user=employee_user,
            date_time=timezone.now(),
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            payment_method='cash',
            status='confirmed',
            commission_rate_snapshot=Decimal('10.00'),
            commission_amount_snapshot=Decimal('10.00')
        )
        period = PayrollPeriod.objects.create(
            employee=employee,
            period_type='biweekly',
            period_start=timezone.localdate() - timedelta(days=5),
            period_end=timezone.localdate() + timedelta(days=5),
            status='open',
            payment_type_snapshot='commission',
            fixed_salary_snapshot=Decimal('0.00'),
            commission_rate_snapshot=Decimal('10.00')
        )
        period.calculate_amounts()
        period.close_period()
        assert period.status == 'pending_approval'
        assert period.net_amount > 0
        return {'tenant': tenant, 'admin': owner, 'period': period}

    def test_approve_period_two_calls_before_refresh(self, setup_data):
        """Dos aprobaciones (simulando dos peticiones concurrentes) sobre el mismo
        período: la primera aprueba, la segunda debe re-leer y rechazarse."""
        period = setup_data['period']
        admin = setup_data['admin']

        # Request A (transacción 1)
        with transaction.atomic():
            locked = PayrollPeriod.objects.select_for_update().get(id=period.id)
            locked.approve(admin)

        period.refresh_from_db()
        assert period.status == 'approved'
        assert period.approved_by_id == admin.id
        assert period.is_finalized is True

        # Request B (transacción 2): re-lee el período y debe fallar (ya aprobado)
        with transaction.atomic():
            locked = PayrollPeriod.objects.select_for_update().get(id=period.id)
            with pytest.raises(ValueError):
                locked.approve(admin)

        period.refresh_from_db()
        assert period.status == 'approved', "El período no debe re-aprobarse"

    def test_approve_period_view_sends_notification_once(self, setup_data):
        """El endpoint aprueba una sola vez y la notificación se envía exactamente una."""
        from unittest import mock
        from rest_framework.test import APIRequestFactory

        period = setup_data['period']
        admin = setup_data['admin']
        tenant = setup_data['tenant']

        request = APIRequestFactory().post(f'/api/employees/client/payroll/{period.id}/approve')
        request.user = admin
        request.tenant = tenant

        with mock.patch.object(PayrollViewSet, '_send_approval_notification') as notify:
            first = PayrollViewSet().approve_period(request, period_id=str(period.id))
            second = PayrollViewSet().approve_period(request, period_id=str(period.id))

        assert first.status_code == 200
        assert second.status_code == 400, "La segunda aprobación debe rechazarse"
        assert notify.call_count == 1, "La notificación debe enviarse una sola vez"

        period.refresh_from_db()
        assert period.status == 'approved'

    def test_approve_period_concurrent_threads_notification_once(self, setup_data):
        """Concurrencia real: varias aprobaciones simultáneas producen UNA notificación."""
        from django.db import connection
        if connection.vendor == 'sqlite':
            pytest.skip('SQLite no soporta select_for_update concurrente real')

        import threading
        from unittest import mock
        from rest_framework.test import APIRequestFactory

        period = setup_data['period']
        admin = setup_data['admin']
        tenant = setup_data['tenant']

        lock = threading.Lock()
        results = []

        def approve_call():
            request = APIRequestFactory().post(f'/api/employees/client/payroll/{period.id}/approve')
            request.user = admin
            request.tenant = tenant
            resp = PayrollViewSet().approve_period(request, period_id=str(period.id))
            with lock:
                results.append(resp.status_code)

        with mock.patch.object(PayrollViewSet, '_send_approval_notification') as notify:
            threads = [threading.Thread(target=approve_call) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

        period.refresh_from_db()
        assert period.status == 'approved'
        assert notify.call_count == 1, f"Notificaciones enviadas: {notify.call_count}"
        assert results.count(200) == 1, f"Aprobaciones exitosas: {results}"