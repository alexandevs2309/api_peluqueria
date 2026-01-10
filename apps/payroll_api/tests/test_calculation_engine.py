"""
Tests deterministas para PayrollCalculationEngine
apps/payroll_api/tests/test_calculation_engine.py
"""
import pytest
from decimal import Decimal
from datetime import date, datetime
from django.utils import timezone
from apps.payroll_api.calculation_engine import PayrollCalculationEngine, PayrollService
from apps.payroll_api.models_new import PayrollPeriod, PayrollCalculation
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import Earning
from apps.tenants_api.models import Tenant
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.mark.django_db
class TestPayrollCalculationEngine:
    
    @pytest.fixture
    def tenant(self):
        return Tenant.objects.create(
            name="Test Salon",
            subdomain="test",
            owner=User.objects.create_user(email="owner@test.com", password="pass")
        )
    
    @pytest.fixture
    def employee_fixed(self, tenant):
        user = User.objects.create_user(
            email="fixed@test.com", 
            password="pass",
            tenant=tenant
        )
        return Employee.objects.create(
            user=user,
            tenant=tenant,
            salary_type='fixed',
            contractual_monthly_salary=Decimal('60000.00'),  # RD$60,000/mes
            payment_frequency='biweekly'
        )
    
    @pytest.fixture
    def employee_commission(self, tenant):
        user = User.objects.create_user(
            email="commission@test.com",
            password="pass", 
            tenant=tenant
        )
        return Employee.objects.create(
            user=user,
            tenant=tenant,
            salary_type='commission',
            commission_percentage=Decimal('40.00'),  # 40%
            payment_frequency='biweekly'
        )
    
    @pytest.fixture
    def employee_mixed(self, tenant):
        user = User.objects.create_user(
            email="mixed@test.com",
            password="pass",
            tenant=tenant
        )
        return Employee.objects.create(
            user=user,
            tenant=tenant,
            salary_type='mixed',
            contractual_monthly_salary=Decimal('30000.00'),  # RD$30,000/mes base
            commission_percentage=Decimal('25.00'),  # 25% comisión
            payment_frequency='biweekly',
            apply_afp=True,
            apply_sfs=True
        )
    
    @pytest.fixture
    def biweekly_period(self, tenant):
        return PayrollPeriod.objects.create(
            tenant=tenant,
            frequency='biweekly',
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 15),
            period_year=2024,
            period_index=1
        )
    
    def test_fixed_salary_calculation(self, employee_fixed, biweekly_period):
        """Test cálculo determinista de salario fijo"""
        engine = PayrollCalculationEngine(employee_fixed, biweekly_period)
        result = engine.calculate()
        
        # Salario quincenal = 60,000 / 2 = 30,000
        assert result['base_salary'] == Decimal('30000.00')
        assert result['commission_total'] == Decimal('0.00')
        assert result['gross_total'] == Decimal('30000.00')
        assert result['net_amount'] == Decimal('30000.00')  # Sin deducciones
        
        # Verificar breakdown
        breakdown = result['breakdown']
        assert breakdown['base_salary']['period_amount'] == '30000.00'
        assert breakdown['commissions']['total'] == Decimal('0.00')
    
    def test_commission_only_calculation(self, employee_commission, biweekly_period):
        """Test cálculo determinista de comisión pura"""
        # Crear earnings del período
        Earning.objects.create(
            employee=employee_commission,
            amount=Decimal('5000.00'),
            service_name='Corte',
            date_earned=datetime(2024, 1, 5, tzinfo=timezone.utc)
        )
        Earning.objects.create(
            employee=employee_commission,
            amount=Decimal('3000.00'),
            service_name='Tinte',
            date_earned=datetime(2024, 1, 10, tzinfo=timezone.utc)
        )
        
        engine = PayrollCalculationEngine(employee_commission, biweekly_period)
        result = engine.calculate()
        
        # Total earnings = 8,000, comisión 40% = 3,200
        assert result['base_salary'] == Decimal('0.00')
        assert result['commission_total'] == Decimal('3200.00')
        assert result['gross_total'] == Decimal('3200.00')
        assert result['net_amount'] == Decimal('3200.00')
        
        # Verificar breakdown detallado
        breakdown = result['breakdown']
        commission_details = breakdown['commissions']['details']
        assert len(commission_details) == 2
        assert commission_details[0]['commission_amount'] == '2000.00'  # 5000 * 0.4
        assert commission_details[1]['commission_amount'] == '1200.00'  # 3000 * 0.4
    
    def test_mixed_salary_with_deductions(self, employee_mixed, biweekly_period):
        """Test cálculo mixto con deducciones legales"""
        # Crear earnings
        Earning.objects.create(
            employee=employee_mixed,
            amount=Decimal('10000.00'),
            service_name='Servicio Premium',
            date_earned=datetime(2024, 1, 15, tzinfo=timezone.utc)  # Último día del período
        )
        
        # Modificar período para ser última quincena del mes
        biweekly_period.period_start = date(2024, 1, 16)
        biweekly_period.period_end = date(2024, 1, 31)
        biweekly_period.save()
        
        engine = PayrollCalculationEngine(employee_mixed, biweekly_period)
        result = engine.calculate()
        
        # Base: 30,000/2 = 15,000
        # Comisión: 10,000 * 0.25 = 2,500
        # Bruto: 17,500
        # AFP: 17,500 * 0.0287 = 502.25
        # SFS: 17,500 * 0.0304 = 532.00
        # Total deducciones: 1,034.25
        # Neto: 16,465.75
        
        assert result['base_salary'] == Decimal('15000.00')
        assert result['commission_total'] == Decimal('2500.00')
        assert result['gross_total'] == Decimal('17500.00')
        assert result['legal_deductions'] == Decimal('1034.25')
        assert result['net_amount'] == Decimal('16465.75')
        
        # Verificar breakdown de deducciones
        breakdown = result['breakdown']
        legal_breakdown = breakdown['deductions']['details']['legal_breakdown']
        assert 'afp' in legal_breakdown
        assert 'sfs' in legal_breakdown
        assert legal_breakdown['afp']['rate'] == '2.87%'
        assert legal_breakdown['sfs']['rate'] == '3.04%'
    
    def test_payroll_service_integration(self, employee_fixed, biweekly_period):
        """Test integración completa con PayrollService"""
        calculation = PayrollService.calculate_payroll(
            employee=employee_fixed,
            period=biweekly_period
        )
        
        # Verificar persistencia
        assert calculation.employee == employee_fixed
        assert calculation.period == biweekly_period
        assert calculation.version == 1
        assert calculation.is_current is True
        assert calculation.base_salary == Decimal('30000.00')
        
        # Verificar breakdown JSON
        breakdown = calculation.calculation_breakdown
        assert 'calculation_metadata' in breakdown
        assert 'base_salary' in breakdown
        assert breakdown['calculation_metadata']['employee_id'] == employee_fixed.id
    
    def test_calculation_versioning(self, employee_fixed, biweekly_period):
        """Test versionado de cálculos"""
        # Primera calculación
        calc1 = PayrollService.calculate_payroll(employee_fixed, biweekly_period)
        assert calc1.version == 1
        assert calc1.is_current is True
        
        # Segunda calculación (recálculo)
        calc2 = PayrollService.calculate_payroll(employee_fixed, biweekly_period)
        assert calc2.version == 2
        assert calc2.is_current is True
        
        # Verificar que la primera ya no es current
        calc1.refresh_from_db()
        assert calc1.is_current is False
    
    def test_no_earnings_commission_employee(self, employee_commission, biweekly_period):
        """Test empleado de comisión sin earnings"""
        engine = PayrollCalculationEngine(employee_commission, biweekly_period)
        result = engine.calculate()
        
        # Sin earnings, sin comisión
        assert result['commission_total'] == Decimal('0.00')
        assert result['gross_total'] == Decimal('0.00')
        assert result['net_amount'] == Decimal('0.00')
        
        # Breakdown debe estar vacío pero estructurado
        breakdown = result['breakdown']
        assert breakdown['commissions']['details'] == []
        assert breakdown['commissions']['total'] == Decimal('0.00')
    
    def test_breakdown_auditability(self, employee_mixed, biweekly_period):
        """Test que el breakdown sea completamente auditable"""
        # Crear múltiples earnings
        earnings_data = [
            (Decimal('2000.00'), 'Corte', datetime(2024, 1, 2, tzinfo=timezone.utc)),
            (Decimal('5000.00'), 'Tinte', datetime(2024, 1, 8, tzinfo=timezone.utc)),
            (Decimal('1500.00'), 'Manicure', datetime(2024, 1, 12, tzinfo=timezone.utc))
        ]
        
        for amount, service, date_earned in earnings_data:
            Earning.objects.create(
                employee=employee_mixed,
                amount=amount,
                service_name=service,
                date_earned=date_earned
            )
        
        engine = PayrollCalculationEngine(employee_mixed, biweekly_period)
        result = engine.calculate()
        
        breakdown = result['breakdown']
        
        # Verificar metadatos completos
        metadata = breakdown['calculation_metadata']
        assert 'employee_id' in metadata
        assert 'period_id' in metadata
        assert 'calculated_at' in metadata
        assert 'salary_type' in metadata
        
        # Verificar detalle de comisiones
        commission_details = breakdown['commissions']['details']
        assert len(commission_details) == 3
        
        # Cada earning debe tener detalle completo
        for detail in commission_details:
            assert 'earning_id' in detail
            assert 'service_name' in detail
            assert 'earning_amount' in detail
            assert 'commission_rate' in detail
            assert 'commission_amount' in detail
            assert 'date' in detail
        
        # Verificar trazabilidad matemática
        total_earnings = sum(Decimal(d['earning_amount']) for d in commission_details)
        total_commission = sum(Decimal(d['commission_amount']) for d in commission_details)
        expected_commission = total_earnings * (employee_mixed.commission_percentage / 100)
        
        assert total_commission == expected_commission
        assert result['commission_total'] == expected_commission