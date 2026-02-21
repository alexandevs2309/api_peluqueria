import pytest
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollPeriod
from apps.employees_api.compensation_models import EmployeeCompensationHistory
from apps.employees_api.adjustment_models import CommissionAdjustment
from apps.pos_api.models import Sale
from apps.tenants_api.models import Tenant
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestPayrollDeterministic:
    """Tests para verificar sistema determinístico de nómina"""
    
    @pytest.fixture
    def setup_data(self):
        """Setup común para todos los tests"""
        owner = User.objects.create_user(email='owner2@test.com', password='pass', full_name='Owner2')
        tenant = Tenant.objects.create(name="Test Tenant", subdomain='test-tenant-deterministic', owner=owner)
        user = User.objects.create_user(
            username="testuser",
            email="test@test.com",
            password="test123",
            tenant=tenant
        )
        
        employee = Employee.objects.create(
            user=user,
            tenant=tenant,
            payment_type='commission',
            commission_rate=Decimal('10.00'),
            fixed_salary=Decimal('0.00')
        )
        
        period = PayrollPeriod.objects.create(
            employee=employee,
            period_type='biweekly',
            period_start=timezone.now().date(),
            period_end=timezone.now().date() + timedelta(days=14),
            status='open'
        )
        
        return {
            'tenant': tenant,
            'user': user,
            'employee': employee,
            'period': period
        }
    
    def test_sale_creates_commission_snapshot(self, setup_data):
        """Test 1: Venta guarda snapshot de comisión"""
        employee = setup_data['employee']
        
        sale = Sale.objects.create(
            employee=employee,
            total=Decimal('100.00'),
            status='confirmed'
        )
        
        # Aplicar snapshot manualmente (en producción lo hace perform_create)
        from apps.pos_api.services import SaleCommissionService
        SaleCommissionService.apply_commission_snapshot(sale, employee)
        sale.save()
        
        assert sale.commission_rate_snapshot == Decimal('10.00')
        assert sale.commission_amount_snapshot == Decimal('10.00')
    
    def test_commission_change_does_not_affect_past_sales(self, setup_data):
        """Test 2: Cambio de comisión futura NO afecta ventas pasadas"""
        employee = setup_data['employee']
        
        # Venta con comisión 10%
        sale1 = Sale.objects.create(
            employee=employee,
            total=Decimal('100.00'),
            status='confirmed'
        )
        from apps.pos_api.services import SaleCommissionService
        SaleCommissionService.apply_commission_snapshot(sale1, employee)
        sale1.save()
        
        original_commission = sale1.commission_amount_snapshot
        
        # Cambiar comisión del empleado
        employee.commission_rate = Decimal('20.00')
        employee.save()
        
        # Recargar venta
        sale1.refresh_from_db()
        
        # Verificar que snapshot NO cambió
        assert sale1.commission_rate_snapshot == Decimal('10.00')
        assert sale1.commission_amount_snapshot == original_commission
    
    def test_refund_creates_negative_adjustment(self, setup_data):
        """Test 3: Refund genera ajuste negativo"""
        employee = setup_data['employee']
        period = setup_data['period']
        user = setup_data['user']
        
        # Crear venta con comisión
        sale = Sale.objects.create(
            employee=employee,
            period=period,
            total=Decimal('100.00'),
            status='confirmed'
        )
        from apps.pos_api.services import SaleCommissionService
        SaleCommissionService.apply_commission_snapshot(sale, employee)
        sale.save()
        
        # Simular refund
        sale.status = 'refunded'
        sale.save()
        
        adjustment = CommissionAdjustment.objects.create(
            sale=sale,
            payroll_period=period,
            employee=employee,
            amount=-sale.commission_amount_snapshot,
            reason='refund',
            created_by=user,
            tenant=setup_data['tenant']
        )
        
        assert adjustment.amount == Decimal('-10.00')
        assert adjustment.reason == 'refund'
    
    def test_finalized_period_does_not_recalculate(self, setup_data):
        """Test 4: Período finalizado NO recalcula"""
        period = setup_data['period']
        
        # Calcular y finalizar
        period.calculate_amounts()
        period.is_finalized = True
        period.save()
        
        original_commission = period.commission_earnings
        
        # Intentar recalcular
        period.calculate_amounts()
        
        # Verificar que NO cambió
        assert period.commission_earnings == original_commission
    
    def test_payroll_uses_snapshots_not_live_data(self, setup_data):
        """Test 5: Payroll usa snapshots, NO datos vivos"""
        employee = setup_data['employee']
        period = setup_data['period']
        
        # Crear venta con snapshot
        sale = Sale.objects.create(
            employee=employee,
            period=period,
            total=Decimal('100.00'),
            status='confirmed'
        )
        from apps.pos_api.services import SaleCommissionService
        SaleCommissionService.apply_commission_snapshot(sale, employee)
        sale.save()
        
        # Cambiar tasa del empleado
        employee.commission_rate = Decimal('50.00')
        employee.save()
        
        # Calcular período usando servicio
        from apps.employees_api.payroll_services import PayrollCalculationService
        calculation = PayrollCalculationService.calculate_from_snapshots(period)
        
        # Verificar que usa snapshot (10%), NO tasa actual (50%)
        assert calculation['commission_earnings'] == Decimal('10.00')
    
    def test_approved_period_blocks_modifications(self, setup_data):
        """Test 6: Período aprobado bloquea modificaciones"""
        period = setup_data['period']
        user = setup_data['user']
        
        # Aprobar período
        period.status = 'pending_approval'
        period.save()
        period.approve(approved_by=user)
        
        # Intentar modificar campo protegido
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            period.base_salary = Decimal('999.99')
            period.save()
    
    def test_adjustment_blocked_on_finalized_period(self, setup_data):
        """Test 7: Ajuste bloqueado en período finalizado"""
        period = setup_data['period']
        employee = setup_data['employee']
        user = setup_data['user']
        
        # Finalizar período
        period.is_finalized = True
        period.save()
        
        # Intentar crear ajuste
        from django.core.exceptions import ValidationError
        with pytest.raises(ValidationError):
            CommissionAdjustment.objects.create(
                payroll_period=period,
                employee=employee,
                amount=Decimal('50.00'),
                reason='bonus',
                created_by=user,
                tenant=setup_data['tenant']
            )
    
    def test_calculation_includes_adjustments(self, setup_data):
        """Test 8: Cálculo incluye ajustes positivos y negativos"""
        employee = setup_data['employee']
        period = setup_data['period']
        user = setup_data['user']
        
        # Venta con comisión
        sale = Sale.objects.create(
            employee=employee,
            period=period,
            total=Decimal('100.00'),
            status='confirmed'
        )
        from apps.pos_api.services import SaleCommissionService
        SaleCommissionService.apply_commission_snapshot(sale, employee)
        sale.save()
        
        # Ajuste positivo (bono)
        CommissionAdjustment.objects.create(
            payroll_period=period,
            employee=employee,
            amount=Decimal('20.00'),
            reason='bonus',
            created_by=user,
            tenant=setup_data['tenant']
        )
        
        # Ajuste negativo (penalización)
        CommissionAdjustment.objects.create(
            payroll_period=period,
            employee=employee,
            amount=Decimal('-5.00'),
            reason='penalty',
            created_by=user,
            tenant=setup_data['tenant']
        )
        
        # Calcular
        from apps.employees_api.payroll_services import PayrollCalculationService
        calculation = PayrollCalculationService.calculate_from_snapshots(period)
        
        # 10 (venta) + 20 (bono) - 5 (penalización) = 25
        assert calculation['commission_earnings'] == Decimal('25.00')
    
    def test_compensation_history_used_for_snapshot(self, setup_data):
        """Test 9: EmployeeCompensationHistory se usa para snapshot"""
        employee = setup_data['employee']
        
        # Crear historial con tasa diferente
        EmployeeCompensationHistory.objects.create(
            employee=employee,
            effective_date=timezone.now().date() - timedelta(days=1),
            payment_type='commission',
            commission_rate=Decimal('15.00'),
            fixed_salary=Decimal('0.00'),
            tenant=setup_data['tenant']
        )
        
        # Crear venta
        sale = Sale.objects.create(
            employee=employee,
            total=Decimal('100.00'),
            status='confirmed'
        )
        from apps.pos_api.services import SaleCommissionService
        SaleCommissionService.apply_commission_snapshot(sale, employee)
        sale.save()
        
        # Debe usar tasa del historial (15%), no del empleado (10%)
        assert sale.commission_rate_snapshot == Decimal('15.00')
        assert sale.commission_amount_snapshot == Decimal('15.00')
    
    def test_approved_period_creates_snapshot(self, setup_data):
        """Test 10: Aprobar período crea calculation_snapshot"""
        period = setup_data['period']
        user = setup_data['user']
        
        period.status = 'pending_approval'
        period.save()
        period.approve(approved_by=user)
        
        assert period.calculation_snapshot is not None
        assert 'calculated_at' in period.calculation_snapshot
        assert 'employee' in period.calculation_snapshot
        assert period.is_finalized is True
