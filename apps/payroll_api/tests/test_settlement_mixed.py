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

class TestSettlementMixed(TestCase):
    
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
            salary_type='mixed',
            salary_amount=Decimal('15000.00'),  # Quincenal
            commission_percentage=Decimal('25.00')
        )
    
    def test_mixed_salary_with_earnings(self):
        """Test salario mixto con earnings"""
        period_start = date(2024, 1, 1)
        period_end = date(2024, 1, 15)
        
        # Crear earnings
        earning = Earning.objects.create(
            employee=self.employee,
            amount=Decimal('2000.00'),
            earning_type='service',
            date_earned=datetime(2024, 1, 5),
            fortnight_year=2024,
            fortnight_number=1
        )
        
        # Cálculo esperado:
        # Salario fijo: 15000
        # Comisión: 2000 * 25% = 500
        # Total: 15500
        expected_total = Decimal('15500.00')
        
        # Sistema Legacy
        legacy_summary = FortnightSummary.objects.create(
            employee=self.employee,
            fortnight_year=2024,
            fortnight_number=1,
            total_earnings=expected_total,
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
            "Salario mixto debe ser exactamente igual"
        )
        self.assertEqual(Decimal('15000.00'), settlement.fixed_salary_amount)
        self.assertEqual(Decimal('500.00'), settlement.commission_amount)
        self.assertEqual(expected_total, settlement.gross_amount)
    
    def test_mixed_salary_no_earnings(self):
        """Test salario mixto sin earnings (solo fijo)"""
        period_start = date(2024, 1, 1)
        period_end = date(2024, 1, 15)
        
        # Sistema Legacy
        legacy_summary = FortnightSummary.objects.create(
            employee=self.employee,
            fortnight_year=2024,
            fortnight_number=1,
            total_earnings=Decimal('15000.00'),  # Solo salario fijo
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
            "Salario mixto sin earnings debe ser exactamente igual"
        )
        self.assertEqual(Decimal('15000.00'), settlement.fixed_salary_amount)
        self.assertEqual(Decimal('0.00'), settlement.commission_amount)
    
    def test_mixed_salary_partial_period(self):
        """Test salario mixto período parcial"""
        period_start = date(2024, 1, 1)
        period_end = date(2024, 1, 10)  # 10 días
        
        # Crear earning
        earning = Earning.objects.create(
            employee=self.employee,
            amount=Decimal('1500.00'),
            earning_type='service',
            date_earned=datetime(2024, 1, 5),
            fortnight_year=2024,
            fortnight_number=1
        )
        
        # Cálculo esperado:
        # Salario fijo prorrateado: 15000 / 15 * 10 = 10000
        # Comisión: 1500 * 25% = 375
        # Total: 10375
        expected_fixed = Decimal('10000.00')
        expected_commission = Decimal('375.00')
        expected_total = Decimal('10375.00')
        
        # Sistema Legacy (simulado)
        days_in_period = 10
        daily_salary = Decimal('15000.00') / 15
        legacy_fixed = daily_salary * days_in_period
        legacy_commission = Decimal('1500.00') * Decimal('0.25')
        legacy_total = legacy_fixed + legacy_commission
        
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
            legacy_total,
            settlement.gross_amount,
            "Salario mixto prorrateado debe ser exactamente igual"
        )
        self.assertEqual(expected_fixed, settlement.fixed_salary_amount)
        self.assertEqual(expected_commission, settlement.commission_amount)
        self.assertEqual(expected_total, settlement.gross_amount)