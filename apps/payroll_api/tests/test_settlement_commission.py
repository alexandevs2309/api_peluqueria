import pytest
from decimal import Decimal
from datetime import datetime, date
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.tenants_api.models import Tenant
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Earning, FortnightSummary
from apps.payroll_api.models import PayrollSettlement, SettlementEarning
from apps.payroll_api.services import PayrollSettlementService

User = get_user_model()

class TestSettlementCommission(TestCase):
    
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
            salary_type='commission',
            salary_amount=Decimal('0.00'),
            commission_percentage=Decimal('40.00')
        )
    
    def test_commission_single_earning(self):
        """Test comisión con un solo earning"""
        period_start = date(2024, 1, 1)
        period_end = date(2024, 1, 15)
        
        # Crear earning
        earning = Earning.objects.create(
            employee=self.employee,
            amount=Decimal('1000.00'),
            earning_type='service',
            date_earned=datetime(2024, 1, 5),
            fortnight_year=2024,
            fortnight_number=1
        )
        
        # Sistema Legacy
        legacy_summary, _ = FortnightSummary.objects.get_or_create(
            employee=self.employee,
            fortnight_year=2024,
            fortnight_number=1,
            defaults={
                'total_earnings': Decimal('400.00'),  # 1000 * 40%
                'is_paid': False
            }
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
            settlement.commission_amount,
            "Comisión simple debe ser exactamente igual"
        )
        self.assertEqual(settlement.gross_amount, settlement.commission_amount)
    
    def test_commission_multiple_earnings(self):
        """Test comisión con múltiples earnings"""
        period_start = date(2024, 1, 1)
        period_end = date(2024, 1, 15)
        
        # Crear múltiples earnings
        earnings = [
            Earning.objects.create(
                employee=self.employee,
                amount=Decimal('500.00'),
                earning_type='service',
                date_earned=datetime(2024, 1, 3),
                fortnight_year=2024,
                fortnight_number=1
            ),
            Earning.objects.create(
                employee=self.employee,
                amount=Decimal('750.00'),
                earning_type='service',
                date_earned=datetime(2024, 1, 8),
                fortnight_year=2024,
                fortnight_number=1
            ),
            Earning.objects.create(
                employee=self.employee,
                amount=Decimal('300.00'),
                earning_type='tip',
                date_earned=datetime(2024, 1, 12),
                fortnight_year=2024,
                fortnight_number=1
            )
        ]
        
        total_earnings = sum(e.amount for e in earnings)  # 1550
        expected_commission = total_earnings * Decimal('0.40')  # 620
        
        # Sistema Legacy
        legacy_summary = FortnightSummary.objects.create(
            employee=self.employee,
            fortnight_year=2024,
            fortnight_number=1,
            total_earnings=expected_commission,
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
            settlement.commission_amount,
            "Comisión múltiple debe ser exactamente igual"
        )
        self.assertEqual(Decimal('620.00'), settlement.commission_amount)
    
    def test_commission_different_rates(self):
        """Test comisión con diferentes porcentajes"""
        # Empleado con 50% comisión
        employee_50 = Employee.objects.create(
            user=User.objects.create_user(
                email="test50@test.com",
                password="test123",
                tenant=self.tenant
            ),
            tenant=self.tenant,
            salary_type='commission',
            salary_amount=Decimal('0.00'),
            commission_percentage=Decimal('50.00')
        )
        
        period_start = date(2024, 1, 1)
        period_end = date(2024, 1, 15)
        
        # Crear earning
        earning = Earning.objects.create(
            employee=employee_50,
            amount=Decimal('2000.00'),
            earning_type='service',
            date_earned=datetime(2024, 1, 5),
            fortnight_year=2024,
            fortnight_number=1
        )
        
        # Sistema Legacy
        legacy_summary = FortnightSummary.objects.create(
            employee=employee_50,
            fortnight_year=2024,
            fortnight_number=1,
            total_earnings=Decimal('1000.00'),  # 2000 * 50%
            is_paid=False
        )
        
        # Sistema Nuevo
        settlement = PayrollSettlement.objects.create(
            employee=employee_50,
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
            settlement.commission_amount,
            "Comisión 50% debe ser exactamente igual"
        )
        self.assertEqual(Decimal('1000.00'), settlement.commission_amount)