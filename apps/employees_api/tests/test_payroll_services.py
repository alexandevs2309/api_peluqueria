import pytest
from decimal import Decimal
from django.contrib.auth import get_user_model
from apps.employees_api.models import Employee
from apps.employees_api.payroll_services import PayrollService
from apps.tenants_api.models import Tenant

User = get_user_model()

@pytest.mark.django_db
class TestPayrollService:
    def test_generate_paystub(self):
        # Setup
        tenant = Tenant.objects.create(name='Test', owner='test@test.com')
        user = User.objects.create(email='emp@test.com', tenant=tenant)
        employee = Employee.objects.create(
            user=user,
            tenant=tenant,
            salary_type='fixed',
            salary_amount=Decimal('15000')
        )
        
        # Execute
        summary = PayrollService.generate_paystub_for_period(
            employee, Decimal('15000'), 2025, 1
        )
        
        # Assert
        assert summary.total_earnings == Decimal('15000')
        assert summary.afp_deduction == Decimal('430.50')
        assert summary.net_salary > Decimal('0')
