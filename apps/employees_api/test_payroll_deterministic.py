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
        owner = User.objects.create_superuser(email='owner2@test.com', password='pass', full_name='Owner2')
        tenant = Tenant.objects.create(name="Test Tenant", subdomain='test-tenant-deterministic', owner=owner)
        user = User.objects.create_user(
            email="test@test.com",
            password="test123",
            tenant=tenant
        )
        
        employee = Employee.objects.create(
            user=user,
            tenant=tenant,
            payment_type='mixed',
            commission_rate=Decimal('10.00'),
            fixed_salary=Decimal('2000.00')
        )
        
        period = PayrollPeriod.objects.create(
            employee=employee,
            period_type='biweekly',
            period_start=timezone.localdate(),
            period_end=timezone.localdate() + timedelta(days=14),
            status='open',
            base_salary=Decimal('1000.00'),
            commission_earnings=Decimal('0.00'),
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('1000.00')
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
            tenant=setup_data['tenant'],
            user=setup_data['user'],
            date_time=timezone.now(),
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            payment_method='cash',
            status='confirmed'
        )
        
        assert sale.commission_rate_snapshot == Decimal('10.00')
        assert sale.commission_amount_snapshot == Decimal('10.00')
    
    def test_commission_change_does_not_affect_past_sales(self, setup_data):
        """Test 2: Cambio de comisión futura NO afecta ventas pasadas"""
        employee = setup_data['employee']
        
        # Venta con comisión 10%
        sale1 = Sale.objects.create(
            employee=employee,
            tenant=setup_data['tenant'],
            user=setup_data['user'],
            date_time=timezone.now(),
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            payment_method='cash',
            status='confirmed'
        )
        
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
        
        # Crear venta con comisión (Sale.save() auto-captura snapshot)
        sale = Sale.objects.create(
            employee=employee,
            tenant=setup_data['tenant'],
            user=setup_data['user'],
            date_time=timezone.now(),
            period=period,
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            payment_method='cash',
            status='confirmed'
        )
        
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
        # Crear venta con comisión (Sale.save() auto-captura snapshot al crear)
        sale = Sale.objects.create(
            employee=employee,
            tenant=setup_data['tenant'],
            user=setup_data['user'],
            date_time=timezone.now(),
            period=period,
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            payment_method='cash',
            status='confirmed'
        )
        
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
        # Crear venta con comisión (Sale.save() auto-captura snapshot al crear)
        sale = Sale.objects.create(
            employee=employee,
            tenant=setup_data['tenant'],
            user=setup_data['user'],
            date_time=timezone.now(),
            period=period,
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            payment_method='cash',
            status='confirmed'
        )
        
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
            effective_date=timezone.localdate() - timedelta(days=1),
            payment_type='commission',
            commission_rate=Decimal('15.00'),
            fixed_salary=Decimal('0.00')
        )
        
        # Crear venta
        sale = Sale.objects.create(
            employee=employee,
            tenant=setup_data['tenant'],
            user=setup_data['user'],
            date_time=timezone.now(),
            total=Decimal('100.00'),
            paid=Decimal('100.00'),
            payment_method='cash',
            status='draft'
        )
        from apps.pos_api.services import SaleCommissionService
        SaleCommissionService.apply_commission_snapshot(sale, employee)
        sale.save()
        sale.status = 'confirmed'
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

    def test_late_minutes_attendance_deduction(self, setup_data):
        """Verifica deducciones de asistencia por tardanzas y fallback a notes"""
        employee = setup_data['employee']
        period = setup_data['period']
        from apps.employees_api.models import AttendanceRecord

        # Crear récord de asistencia con late_minutes
        AttendanceRecord.objects.create(
            employee=employee,
            work_date=period.period_start,
            status='late',
            late_minutes=45,
            notes='Tardanza'
        )

        # Crear récord legacy que use fallback a notas
        AttendanceRecord.objects.create(
            employee=employee,
            work_date=period.period_start + timedelta(days=1),
            status='late',
            late_minutes=0,
            notes='Retraso de 15 minutos'
        )

        period.calculate_amounts()
        period.save()

        # Deducción total esperada para (45 + 15) = 60 minutos
        # Salario fijo: 2000.00
        # Salario diario = 2000 / 23.83 = 83.9278
        # Valor minuto = 83.9278 / 480 = 0.1748
        # Deducción por 60 min = 0.1748 * 60 = 10.49
        deductions = period.deductions.filter(is_automatic=True)
        assert deductions.exists()
        deduction_tardanza = deductions.filter(description__contains="tardanza").first()
        assert deduction_tardanza is not None
        assert abs(deduction_tardanza.amount - Decimal('10.49')) < Decimal('0.05')

    def test_auto_loan_deduction_and_payment_reconciliation(self, setup_data):
        """Verifica que el préstamo se descuenta del periodo y rebaja balance al pagar"""
        employee = setup_data['employee']
        period = setup_data['period']
        user = setup_data['user']
        from apps.employees_api.models import Loan

        loan = Loan.objects.create(
            employee=employee,
            amount=Decimal('1000.00'),
            installments=2,
            remaining_balance=Decimal('1000.00'),
            status='active',
            description='Prestamo test'
        )

        period.calculate_amounts()
        period.save()

        # Verificar que se creó cuota de deducción por 500
        deductions = period.deductions.filter(is_automatic=True, deduction_type='loan')
        assert deductions.count() == 1
        assert deductions.first().amount == Decimal('500.00')

        # Registrar pago para disparar conciliación de préstamo
        period.status = 'pending_approval'
        period.save()
        period.approve(approved_by=user)
        
        period.mark_as_paid(payment_method='cash', payment_reference='REF-1', paid_by=user)
        
        loan.refresh_from_db()
        assert loan.remaining_balance == Decimal('500.00')
        assert loan.status == 'active'

        # Siguiente periodo paga lo restante
        period2 = PayrollPeriod.objects.create(
            employee=employee,
            period_type='biweekly',
            period_start=period.period_end + timedelta(days=1),
            period_end=period.period_end + timedelta(days=15),
            status='open'
        )
        period2.calculate_amounts()
        period2.save()

        period2.status = 'pending_approval'
        period2.save()
        period2.approve(approved_by=user)
        period2.mark_as_paid(payment_method='cash', payment_reference='REF-2', paid_by=user)

        loan.refresh_from_db()
        assert loan.remaining_balance == Decimal('0.00')
        assert loan.status == 'paid'

    def test_payroll_configuration_auto_deduction(self, setup_data):
        """Verifica deducciones automáticas de impuestos basadas en la configuración del tenant"""
        employee = setup_data['employee']
        period = setup_data['period']
        from apps.employees_api.earnings_models import PayrollConfiguration

        # Configurar tasas para el tenant
        PayrollConfiguration.objects.update_or_create(
            tenant=setup_data['tenant'],
            defaults={
                'tax_rate': Decimal('1.50'),
                'social_security_rate': Decimal('2.00'),
                'health_insurance_rate': Decimal('1.00')
            }
        )

        period.calculate_amounts()
        period.save()

        # Salario base es 1000.00
        # ISR = 1000 * 1.5% = 15.00
        # TSS = 1000 * 2.0% = 20.00
        # SFS = 1000 * 1.0% = 10.00
        assert period.deductions.filter(deduction_type='tax', amount=Decimal('15.00')).exists()
        assert period.deductions.filter(deduction_type='social_security', amount=Decimal('20.00')).exists()
        assert period.deductions.filter(deduction_type='health_insurance', amount=Decimal('10.00')).exists()
        assert period.deductions_total >= Decimal('45.00')

