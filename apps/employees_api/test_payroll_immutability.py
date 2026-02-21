import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from decimal import Decimal
from apps.employees_api.earnings_models import PayrollPeriod
from apps.employees_api.models import Employee
from apps.auth_api.models import User
from apps.tenants_api.models import Tenant


@pytest.mark.django_db
class TestPayrollPeriodImmutability:
    """Tests para verificar inmutabilidad de PayrollPeriod"""
    
    @pytest.fixture
    def tenant(self):
        owner = User.objects.create_user(email="owner@test.com", password="ownerpass", full_name="Owner")
        return Tenant.objects.create(name="Test Tenant", subdomain="test-tenant-immutability", owner=owner)
    
    @pytest.fixture
    def user(self, tenant):
        return User.objects.create_user(
            email="test@test.com",
            password="test123",
            full_name="Test User",
            tenant=tenant
        )
    
    @pytest.fixture
    def employee(self, user, tenant):
        return Employee.objects.create(
            user=user,
            tenant=tenant,
            payment_type='commission',
            commission_rate=Decimal('40.00')
        )
    
    @pytest.fixture
    def period(self, employee):
        today = timezone.now().date()
        return PayrollPeriod.objects.create(
            employee=employee,
            period_type='biweekly',
            period_start=today.replace(day=1),
            period_end=today.replace(day=15),
            status='open',
            base_salary=Decimal('1000.00'),
            commission_earnings=Decimal('500.00'),
            gross_amount=Decimal('1500.00'),
            net_amount=Decimal('1500.00')
        )
    
    def test_can_modify_open_period(self, period):
        """Período abierto puede modificarse"""
        period.base_salary = Decimal('2000.00')
        period.save()  # No debe lanzar error
        
        period.refresh_from_db()
        assert period.base_salary == Decimal('2000.00')
    
    def test_cannot_modify_approved_period_amounts(self, period, user):
        """Período aprobado NO puede modificar montos"""
        # Aprobar período
        period.status = 'approved'
        period.approved_by = user
        period.approved_at = timezone.now()
        period.save()
        
        # Intentar modificar monto
        period.base_salary = Decimal('2000.00')
        
        with pytest.raises(ValidationError) as exc_info:
            period.save()
        
        assert "base_salary" in str(exc_info.value)
    
    def test_cannot_modify_approved_period_dates(self, period, user):
        """Período aprobado NO puede modificar fechas"""
        # Aprobar período
        period.status = 'approved'
        period.approved_by = user
        period.approved_at = timezone.now()
        period.save()
        
        # Intentar modificar fechas
        period.period_start = timezone.now().date().replace(day=2)
        
        with pytest.raises(ValidationError) as exc_info:
            period.save()
        
        assert "period_start" in str(exc_info.value)
    
    def test_cannot_modify_approved_period_employee(self, period, user, employee):
        """Período aprobado NO puede cambiar empleado"""
        # Aprobar período
        period.status = 'approved'
        period.approved_by = user
        period.approved_at = timezone.now()
        period.save()
        
        # Crear otro empleado
        other_user = User.objects.create_user(
            email="other@test.com",
            password="test123",
            full_name="Other User",
            tenant=employee.tenant
        )
        other_employee = Employee.objects.create(
            user=other_user,
            tenant=employee.tenant
        )
        
        # Intentar cambiar empleado
        period.employee = other_employee
        
        with pytest.raises(ValidationError) as exc_info:
            period.save()
        
        assert "employee" in str(exc_info.value)
    
    def test_can_transition_approved_to_paid(self, period, user):
        """Período aprobado PUEDE cambiar a pagado"""
        # Aprobar período
        period.status = 'approved'
        period.approved_by = user
        period.approved_at = timezone.now()
        period.save()
        
        # Cambiar a pagado (transición permitida)
        period.status = 'paid'
        period.payment_method = 'cash'
        period.payment_reference = 'REF123'
        period.paid_at = timezone.now()
        period.paid_by = user
        period.save()  # No debe lanzar error
        
        period.refresh_from_db()
        assert period.status == 'paid'
    
    def test_cannot_modify_paid_period(self, period, user):
        """Período pagado NO puede modificarse"""
        # Aprobar y pagar período
        period.status = 'approved'
        period.approved_by = user
        period.approved_at = timezone.now()
        period.save()
        
        period.status = 'paid'
        period.payment_method = 'cash'
        period.paid_at = timezone.now()
        period.paid_by = user
        period.save()
        
        # Intentar modificar monto
        period.net_amount = Decimal('2000.00')
        
        with pytest.raises(ValidationError) as exc_info:
            period.save()
        
        assert "net_amount" in str(exc_info.value)
    
    def test_cannot_change_status_from_paid(self, period, user):
        """Período pagado NO puede cambiar de status"""
        # Aprobar y pagar período
        period.status = 'approved'
        period.approved_by = user
        period.approved_at = timezone.now()
        period.save()
        
        period.status = 'paid'
        period.payment_method = 'cash'
        period.paid_at = timezone.now()
        period.paid_by = user
        period.save()
        
        # Intentar cambiar status
        period.status = 'open'
        
        with pytest.raises(ValidationError) as exc_info:
            period.save()
        
        assert "Transición de estado no permitida" in str(exc_info.value)
    
    def test_can_update_notifications_on_approved_period(self, period, user):
        """Período aprobado PUEDE actualizar notificaciones"""
        # Aprobar período
        period.status = 'approved'
        period.approved_by = user
        period.approved_at = timezone.now()
        period.save()
        
        # Actualizar notificación (permitido)
        period.notification_sent = True
        period.notification_sent_at = timezone.now()
        period.save()  # No debe lanzar error
        
        period.refresh_from_db()
        assert period.notification_sent is True
    
    def test_cannot_modify_calculation_snapshot_on_approved_period(self, period, user):
        """Período aprobado NO puede modificar snapshot"""
        # Aprobar período con snapshot
        period.status = 'approved'
        period.approved_by = user
        period.approved_at = timezone.now()
        period.calculation_snapshot = {'test': 'data'}
        period.save()
        
        # Intentar modificar snapshot
        period.calculation_snapshot = {'modified': 'data'}
        
        with pytest.raises(ValidationError) as exc_info:
            period.save()
        
        assert "calculation_snapshot" in str(exc_info.value)
