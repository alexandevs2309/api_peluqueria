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

class TestSettlementVsLegacy(TestCase):
    """
    Tests comparativos directos entre FortnightSummary (legacy) 
    y PayrollSettlement (nuevo) para garantizar equivalencia matemática
    """
    
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
    
    def test_legacy_vs_new_fixed_salary(self):
        """Comparación directa: salario fijo"""
        employee = self.create_employee('fixed', Decimal('25000.00'), Decimal('0.00'), '1')
        
        period_start = date(2024, 1, 1)
        period_end = date(2024, 1, 15)
        
        # Sistema Legacy
        legacy_summary = FortnightSummary.objects.create(
            employee=employee,
            fortnight_year=2024,
            fortnight_number=1,
            total_earnings=Decimal('25000.00'),
            is_paid=False
        )
        
        # Sistema Nuevo
        settlement = PayrollSettlement.objects.create(
            employee=employee,
            tenant=self.tenant,
            frequency='biweekly',
            period_start=period_start,
            period_end=period_end,
            period_year=2024,
            period_index=1
        )
        
        service = PayrollSettlementService()
        service.calculate_settlement(settlement)
        
        # COMPARACIÓN CRÍTICA
        self.assertEqual(
            legacy_summary.total_earnings,
            settlement.gross_amount,
            f"FALLO CRÍTICO: Legacy={legacy_summary.total_earnings}, Nuevo={settlement.gross_amount}"
        )
    
    def test_legacy_vs_new_commission_only(self):
        """Comparación directa: solo comisión"""
        employee = self.create_employee('commission', Decimal('0.00'), Decimal('40.00'), '2')
        
        # Crear earnings
        earnings_data = [
            (Decimal('800.00'), datetime(2024, 1, 3)),
            (Decimal('1200.00'), datetime(2024, 1, 8)),
            (Decimal('600.00'), datetime(2024, 1, 12))
        ]
        
        total_earnings = Decimal('0.00')
        for amount, date_earned in earnings_data:
            Earning.objects.create(
                employee=employee,
                amount=amount,
                earning_type='service',
                date_earned=date_earned,
                fortnight_year=2024,
                fortnight_number=1
            )
            total_earnings += amount
        
        expected_commission = total_earnings * Decimal('0.40')  # 1040.00
        
        # Sistema Legacy
        legacy_summary = FortnightSummary.objects.create(
            employee=employee,
            fortnight_year=2024,
            fortnight_number=1,
            total_earnings=expected_commission,
            is_paid=False
        )
        
        # Sistema Nuevo
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
        
        # COMPARACIÓN CRÍTICA
        self.assertEqual(
            legacy_summary.total_earnings,
            settlement.gross_amount,
            f"FALLO CRÍTICO: Legacy={legacy_summary.total_earnings}, Nuevo={settlement.gross_amount}"
        )
        self.assertEqual(expected_commission, settlement.commission_amount)
    
    def test_legacy_vs_new_mixed_salary(self):
        """Comparación directa: salario mixto"""
        employee = self.create_employee('mixed', Decimal('20000.00'), Decimal('30.00'), '3')
        
        # Crear earnings
        earning = Earning.objects.create(
            employee=employee,
            amount=Decimal('3000.00'),
            earning_type='service',
            date_earned=datetime(2024, 1, 10),
            fortnight_year=2024,
            fortnight_number=1
        )
        
        # Cálculo esperado:
        # Fijo: 20000
        # Comisión: 3000 * 30% = 900
        # Total: 20900
        expected_total = Decimal('20900.00')
        
        # Sistema Legacy
        legacy_summary = FortnightSummary.objects.create(
            employee=employee,
            fortnight_year=2024,
            fortnight_number=1,
            total_earnings=expected_total,
            is_paid=False
        )
        
        # Sistema Nuevo
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
        
        # COMPARACIÓN CRÍTICA
        self.assertEqual(
            legacy_summary.total_earnings,
            settlement.gross_amount,
            f"FALLO CRÍTICO: Legacy={legacy_summary.total_earnings}, Nuevo={settlement.gross_amount}"
        )
    
    def test_edge_case_zero_earnings(self):
        """Caso límite: empleado sin earnings"""
        employee = self.create_employee('commission', Decimal('0.00'), Decimal('50.00'), '4')
        
        # Sistema Legacy
        legacy_summary = FortnightSummary.objects.create(
            employee=employee,
            fortnight_year=2024,
            fortnight_number=1,
            total_earnings=Decimal('0.00'),
            is_paid=False
        )
        
        # Sistema Nuevo
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
        
        # COMPARACIÓN CRÍTICA
        self.assertEqual(
            legacy_summary.total_earnings,
            settlement.gross_amount,
            f"FALLO CRÍTICO: Legacy={legacy_summary.total_earnings}, Nuevo={settlement.gross_amount}"
        )
    
    def test_multiple_employees_batch(self):
        """Test batch: múltiples empleados diferentes tipos"""
        employees_config = [
            ('fixed', Decimal('18000.00'), Decimal('0.00')),
            ('commission', Decimal('0.00'), Decimal('45.00')),
            ('mixed', Decimal('12000.00'), Decimal('20.00'))
        ]
        
        for i, (salary_type, salary_amount, commission_rate) in enumerate(employees_config):
            employee = self.create_employee(salary_type, salary_amount, commission_rate, str(i+5))
            
            # Crear earning para todos
            if salary_type != 'fixed':
                Earning.objects.create(
                    employee=employee,
                    amount=Decimal('1000.00'),
                    earning_type='service',
                    date_earned=datetime(2024, 1, 5),
                    fortnight_year=2024,
                    fortnight_number=1
                )
            
            # Calcular expected según tipo
            if salary_type == 'fixed':
                expected = salary_amount
            elif salary_type == 'commission':
                expected = Decimal('1000.00') * (commission_rate / 100)
            else:  # mixed
                expected = salary_amount + (Decimal('1000.00') * (commission_rate / 100))
            
            # Sistema Legacy
            legacy_summary = FortnightSummary.objects.create(
                employee=employee,
                fortnight_year=2024,
                fortnight_number=1,
                total_earnings=expected,
                is_paid=False
            )
            
            # Sistema Nuevo
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
            
            # COMPARACIÓN CRÍTICA
            self.assertEqual(
                legacy_summary.total_earnings,
                settlement.gross_amount,
                f"FALLO CRÍTICO empleado {i+1} ({salary_type}): Legacy={legacy_summary.total_earnings}, Nuevo={settlement.gross_amount}"
            )