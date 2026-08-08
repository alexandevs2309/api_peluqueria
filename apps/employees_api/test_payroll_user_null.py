import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollPeriod, PayrollDeduction
from apps.pos_api.models import Sale
from apps.tenants_api.models import Tenant
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestPayrollUserNull:
    """Pruebas unitarias para validar cálculo de nómina con usuarios NULL y transiciones"""

    @pytest.fixture
    def setup_data(self):
        # Crear tenants y usuarios
        owner = User.objects.create_superuser(email='owner_test@test.com', password='pass', full_name='Owner Test')
        tenant_a = Tenant.objects.create(name="Tenant A", subdomain='tenant-a', owner=owner)
        tenant_b = Tenant.objects.create(name="Tenant B", subdomain='tenant-b', owner=owner)
        
        user_a = User.objects.create_user(email="user_a@test.com", password="password", tenant=tenant_a)
        
        # Empleado tipo comisionista en Tenant A
        employee = Employee.objects.create(
            user=user_a,
            tenant=tenant_a,
            payment_type='commission',
            commission_rate=Decimal('10.00'),
            fixed_salary=Decimal('0.00')
        )
        
        # Periodo de nómina abierto para el empleado
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
        
        return {
            'tenant_a': tenant_a,
            'tenant_b': tenant_b,
            'user_a': user_a,
            'employee': employee,
            'period': period
        }

    def test_payroll_user_null_and_transitions(self, setup_data):
        employee = setup_data['employee']
        tenant_a = setup_data['tenant_a']
        tenant_b = setup_data['tenant_b']
        user_a = setup_data['user_a']
        period = setup_data['period']

        # Caso A: Venta con user NULL (Debe incluirse)
        sale_null_user = Sale.objects.create(
            employee=employee,
            tenant=tenant_a,
            user=None,
            date_time=timezone.now(),
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            payment_method='cash',
            status='confirmed',
            commission_rate_snapshot=Decimal('10.00'),
            commission_amount_snapshot=Decimal('10.00')
        )

        # Caso B: Venta con user válido (Debe incluirse)
        sale_valid_user = Sale.objects.create(
            employee=employee,
            tenant=tenant_a,
            user=user_a,
            date_time=timezone.now(),
            total=Decimal('200.00'),
            paid=Decimal('200.00'),
            payment_method='cash',
            status='confirmed',
            commission_rate_snapshot=Decimal('10.00'),
            commission_amount_snapshot=Decimal('20.00')
        )

        # Caso C: Venta de otro tenant (NO debe incluirse)
        sale_other_tenant = Sale.objects.create(
            employee=employee,
            tenant=tenant_b,
            user=None,
            date_time=timezone.now(),
            total=Decimal('500.00'),
            paid=Decimal('500.00'),
            payment_method='cash',
            status='confirmed',
            commission_rate_snapshot=Decimal('10.00'),
            commission_amount_snapshot=Decimal('50.00')
        )

        # Caso D: Período abierto (gross > 0)
        period.calculate_amounts()
        
        # Validar comisiones agregadas (10.00 de sale_null_user + 20.00 de sale_valid_user = 30.00)
        # La del tenant B debe ser ignorada.
        assert period.commission_earnings == Decimal('30.00')
        assert period.gross_amount == Decimal('30.00')
        assert period.gross_amount > 0

        # Crear una deducción manual para verificar el cálculo del neto
        PayrollDeduction.objects.create(
            period=period,
            deduction_type='other',
            amount=Decimal('5.00'),
            description="Deducción de prueba"
        )
        
        period.calculate_amounts()
        # Caso G: net sigue siendo correcto (30.00 gross - 5.00 deduction = 25.00 net)
        assert period.net_amount == Decimal('25.00')

        # Caso E: Enviar período (gross NO cambia)
        gross_before_submit = period.gross_amount
        period.close_period()
        assert period.status == 'pending_approval'
        assert period.gross_amount == gross_before_submit
        assert period.net_amount == Decimal('25.00')

        # Caso F: Aprobar (gross sigue igual)
        period.approve(approved_by=setup_data['user_a'])
        assert period.status == 'approved'
        assert period.gross_amount == gross_before_submit
        assert period.net_amount == Decimal('25.00')
