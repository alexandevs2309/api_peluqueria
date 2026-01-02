import pytest
from decimal import Decimal
from datetime import datetime, date
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.tenants_api.models import Tenant
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Earning, FortnightSummary
from apps.payroll_api.models import PayrollSettlement
from apps.payroll_api.services import PayrollSettlementService

User = get_user_model()

class TestSettlementFixedSalary(TestCase):
    
    def setUp(self):
        # Crear owner primero
        self.owner = User.objects.create_user(
            email="owner@test.com",
            password="test123"
        )
        self.tenant = Tenant.objects.create(
            name="Test Salon",
            owner=self.owner
        )
        self.user = User.objects.create_user(
            email="test@test.com",
            password="test123",
            tenant=self.tenant
        )
        self.employee = Employee.objects.create(
            user=self.user,
            tenant=self.tenant,
            salary_type='fixed',
            salary_amount=Decimal('30000.00'),  # Quincenal
            commission_percentage=Decimal('0.00')
        )
    
    def test_fixed_salary_full_period(self):
        """Test salario fijo período completo (1-15)"""
        period_start = date(2024, 1, 1)
        period_end = date(2024, 1, 15)
        
        # Sistema Legacy
        legacy_summary = FortnightSummary.objects.create(
            employee=self.employee,
            fortnight_year=2024,
            fortnight_number=1,
            total_earnings=Decimal('30000.00'),
            is_paid=False
        )
        
        # Sistema Nuevo
        settlement = PayrollSettlement.objects.create(
            employee=self.employee,
            tenant=self.tenant,
            frequency='biweekly',
            period_start=period_start,
            period_end=period_end,
            period_year=2024,
            period_index=1
        )
        
        service = PayrollSettlementService()
        service.calculate_settlement(settlement)
        
        # COMPARACIÓN EXACTA
        self.assertEqual(
            legacy_summary.total_earnings,
            settlement.gross_amount,
            "Salario fijo completo debe ser exactamente igual"
        )
    
    def test_fixed_salary_partial_period(self):
        """Test salario fijo período parcial (5 días)"""
        period_start = date(2024, 1, 1)
        period_end = date(2024, 1, 5)
        
        # Cálculo manual esperado: 30000 / 15 * 5 = 10000
        expected_amount = Decimal('10000.00')
        
        # Sistema Legacy (simulado)
        days_in_period = 5
        daily_salary = Decimal('30000.00') / 15
        legacy_amount = daily_salary * days_in_period
        
        # Sistema Nuevo
        settlement = PayrollSettlement.objects.create(
            employee=self.employee,
            tenant=self.tenant,
            frequency='biweekly',
            period_start=period_start,
            period_end=period_end,
            period_year=2024,
            period_index=1
        )
        
        service = PayrollSettlementService()
        service.calculate_settlement(settlement)
        
        # COMPARACIÓN EXACTA
        self.assertEqual(
            legacy_amount,
            settlement.gross_amount,
            "Salario fijo prorrateado debe ser exactamente igual"
        )
        self.assertEqual(expected_amount, settlement.gross_amount)
    
    def test_fixed_salary_second_fortnight(self):
        """Test salario fijo segunda quincena (16-31)"""
        period_start = date(2024, 1, 16)
        period_end = date(2024, 1, 31)
        
        # Sistema Legacy
        legacy_summary = FortnightSummary.objects.create(
            employee=self.employee,
            fortnight_year=2024,
            fortnight_number=2,
            total_earnings=Decimal('30000.00'),
            is_paid=False
        )
        
        # Sistema Nuevo
        settlement = PayrollSettlement.objects.create(
            employee=self.employee,
            tenant=self.tenant,
            frequency='biweekly',
            period_start=period_start,
            period_end=period_end,
            period_year=2024,
            period_index=2
        )
        
        service = PayrollSettlementService()
        service.calculate_settlement(settlement)
        
        # COMPARACIÓN EXACTA
        self.assertEqual(
            legacy_summary.total_earnings,
            settlement.gross_amount,
            "Segunda quincena debe ser exactamente igual"
        )