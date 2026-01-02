import pytest
from decimal import Decimal
from datetime import datetime, date
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.tenants_api.models import Tenant
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Earning
from apps.payroll_api.models import PayrollSettlement
from apps.payroll_api.services import PayrollSettlementService

User = get_user_model()

class TestPayrollEquivalence(TestCase):
    """
    Test crítico: Verificar equivalencia matemática entre legacy y nuevo sistema
    SIN crear FortnightSummary para evitar conflictos con signals
    """
    
    def setUp(self):
        self.owner = User.objects.create_user(
            email="owner@test.com",
            password="test123"
        )
        self.tenant = Tenant.objects.create(
            name="Test Salon",
            owner=self.owner
        )
    
    def create_employee(self, salary_type, salary_amount, commission_percentage, email_suffix=""):
        user = User.objects.create_user(
            email=f"test{email_suffix}@test.com",
            password="test123",
            tenant=self.tenant
        )
        return Employee.objects.create(
            user=user,
            tenant=self.tenant,
            salary_type=salary_type,
            salary_amount=salary_amount,
            commission_percentage=commission_percentage
        )
    
    def test_fixed_salary_calculation(self):
        """Test cálculo directo salario fijo"""
        employee = self.create_employee('fixed', Decimal('30000.00'), Decimal('0.00'), '1')
        
        settlement = PayrollSettlement.objects.create(
            employee=employee,
            tenant=self.tenant,
            frequency='biweekly',
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 15),
            period_year=2024,
            period_index=1
        )
        
        service = PayrollSettlementService()
        service.calculate_settlement(settlement)
        
        # VERIFICACIÓN CRÍTICA: Salario fijo completo
        self.assertEqual(Decimal('30000.00'), settlement.gross_amount)
        self.assertEqual(Decimal('30000.00'), settlement.fixed_salary_amount)
        self.assertEqual(Decimal('0.00'), settlement.commission_amount)
    
    def test_commission_calculation(self):
        """Test cálculo directo comisión"""
        employee = self.create_employee('commission', Decimal('0.00'), Decimal('40.00'), '2')
        
        # Crear earning
        earning = Earning.objects.create(
            employee=employee,
            amount=Decimal('1000.00'),
            earning_type='service',
            date_earned=datetime(2024, 1, 5),
            fortnight_year=2024,
            fortnight_number=1
        )
        
        settlement = PayrollSettlement.objects.create(
            employee=employee,
            tenant=self.tenant,
            frequency='biweekly',
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 15),
            period_year=2024,
            period_index=1
        )
        
        service = PayrollSettlementService()
        service.calculate_settlement(settlement)
        
        # VERIFICACIÓN CRÍTICA: Comisión 40%
        expected_commission = Decimal('1000.00') * Decimal('0.40')
        self.assertEqual(expected_commission, settlement.commission_amount)
        self.assertEqual(expected_commission, settlement.gross_amount)
        self.assertEqual(Decimal('0.00'), settlement.fixed_salary_amount)
    
    def test_mixed_salary_calculation(self):
        """Test cálculo directo salario mixto"""
        employee = self.create_employee('mixed', Decimal('15000.00'), Decimal('25.00'), '3')
        
        # Crear earning
        earning = Earning.objects.create(
            employee=employee,
            amount=Decimal('2000.00'),
            earning_type='service',
            date_earned=datetime(2024, 1, 10),
            fortnight_year=2024,
            fortnight_number=1
        )
        
        settlement = PayrollSettlement.objects.create(
            employee=employee,
            tenant=self.tenant,
            frequency='biweekly',
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 15),
            period_year=2024,
            period_index=1
        )
        
        service = PayrollSettlementService()
        service.calculate_settlement(settlement)
        
        # VERIFICACIÓN CRÍTICA: Fijo + Comisión
        expected_fixed = Decimal('15000.00')
        expected_commission = Decimal('2000.00') * Decimal('0.25')
        expected_total = expected_fixed + expected_commission
        
        self.assertEqual(expected_fixed, settlement.fixed_salary_amount)
        self.assertEqual(expected_commission, settlement.commission_amount)
        self.assertEqual(expected_total, settlement.gross_amount)
    
    def test_partial_period_proration(self):
        """Test prorrateo período parcial"""
        employee = self.create_employee('fixed', Decimal('30000.00'), Decimal('0.00'), '4')
        
        settlement = PayrollSettlement.objects.create(
            employee=employee,
            tenant=self.tenant,
            frequency='biweekly',
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 5),  # 5 días
            period_year=2024,
            period_index=1
        )
        
        service = PayrollSettlementService()
        service.calculate_settlement(settlement)
        
        # VERIFICACIÓN CRÍTICA: Prorrateo 5/15 días
        expected_amount = Decimal('30000.00') / 15 * 5
        self.assertEqual(expected_amount, settlement.gross_amount)
    
    def test_multiple_earnings_aggregation(self):
        """Test agregación múltiples earnings"""
        employee = self.create_employee('commission', Decimal('0.00'), Decimal('50.00'), '5')
        
        # Crear múltiples earnings
        earnings_amounts = [Decimal('500.00'), Decimal('750.00'), Decimal('300.00')]
        for i, amount in enumerate(earnings_amounts):
            Earning.objects.create(
                employee=employee,
                amount=amount,
                earning_type='service',
                date_earned=datetime(2024, 1, 3 + i),
                fortnight_year=2024,
                fortnight_number=1
            )
        
        settlement = PayrollSettlement.objects.create(
            employee=employee,
            tenant=self.tenant,
            frequency='biweekly',
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 15),
            period_year=2024,
            period_index=1
        )
        
        service = PayrollSettlementService()
        service.calculate_settlement(settlement)
        
        # VERIFICACIÓN CRÍTICA: Suma total * comisión
        total_earnings = sum(earnings_amounts)
        expected_commission = total_earnings * Decimal('0.50')
        
        self.assertEqual(expected_commission, settlement.commission_amount)
        self.assertEqual(expected_commission, settlement.gross_amount)