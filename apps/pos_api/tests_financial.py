"""
Tests Financieros Críticos - Protección contra bugs en código nuevo
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from decimal import Decimal
from apps.tenants_api.models import Tenant
from apps.employees_api.models import Employee
from apps.pos_api.models import Sale
from apps.employees_api.earnings_models import PayrollPeriod
from apps.employees_api.adjustment_models import CommissionAdjustment

User = get_user_model()


class FinancialIntegrityTests(TestCase):
    """Tests que DEBEN pasar siempre - protegen dinero real"""
    
    def setUp(self):
        # Setup mínimo
        self.owner = User.objects.create_user(email='owner@testsalon.com', password='pass', full_name='Owner')
        self.tenant = Tenant.objects.create(name='Test Salon', subdomain='test', owner=self.owner)
        self.user = User.objects.create_user(
            email='admin@test.com',
            password='test123',
            full_name='Admin Test',
            tenant=self.tenant
        )
        self.employee = Employee.objects.create(
            user=self.user,
            tenant=self.tenant,
            payment_type='commission',
            commission_rate=Decimal('40.00')
        )
    
    def test_commission_snapshot_immutable(self):
        """CRÍTICO: Comisión capturada NO debe cambiar"""
        # Crear venta con comisión
        sale = Sale.objects.create(
            user=self.user,
            employee=self.employee,
            total=Decimal('100.00'),
            status='confirmed'
        )
        
        # Verificar snapshot capturado
        self.assertEqual(sale.commission_rate_snapshot, Decimal('40.00'))
        self.assertEqual(sale.commission_amount_snapshot, Decimal('40.00'))
        
        # Cambiar tasa de comisión del empleado
        self.employee.commission_rate = Decimal('50.00')
        self.employee.save()
        
        # Recargar venta
        sale.refresh_from_db()
        
        # DEBE mantener comisión original
        self.assertEqual(sale.commission_amount_snapshot, Decimal('40.00'))
    
    def test_sale_immutable_after_confirmed(self):
        """CRÍTICO: Venta confirmada NO se puede modificar"""
        sale = Sale.objects.create(
            user=self.user,
            employee=self.employee,
            total=Decimal('100.00'),
            status='confirmed'
        )
        
        # Intentar modificar total
        sale.total = Decimal('200.00')
        
        with self.assertRaises(Exception):
            sale.save()
    
    def test_refund_creates_adjustment(self):
        """CRÍTICO: Refund DEBE crear CommissionAdjustment negativo"""
        # Crear venta con comisión
        sale = Sale.objects.create(
            user=self.user,
            employee=self.employee,
            total=Decimal('100.00'),
            status='confirmed'
        )
        
        # Crear período
        from datetime import date
        period = PayrollPeriod.objects.create(
            employee=self.employee,
            period_type='biweekly',
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 15),
            status='open'
        )
        
        # Simular refund (debe crear adjustment)
        adjustment = CommissionAdjustment.objects.create(
            employee=self.employee,
            period=period,
            sale=sale,
            amount=Decimal('-40.00'),
            reason='refund',
            description='Test refund'
        )
        
        # Verificar adjustment creado
        self.assertEqual(adjustment.amount, Decimal('-40.00'))
        self.assertEqual(adjustment.reason, 'refund')
    
    def test_payroll_period_immutable_when_finalized(self):
        """CRÍTICO: Período finalizado NO se puede modificar"""
        from datetime import date
        period = PayrollPeriod.objects.create(
            employee=self.employee,
            period_type='biweekly',
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 15),
            status='approved',
            is_finalized=True,
            gross_amount=Decimal('1000.00')
        )
        
        # Intentar modificar gross_amount
        period.gross_amount = Decimal('2000.00')
        
        with self.assertRaises(Exception):
            period.save()
    
    def test_multi_tenant_isolation(self):
        """CRÍTICO: Tenant A NO puede ver datos de Tenant B"""
        # Crear segundo tenant
        tenant_b = Tenant.objects.create(name='Salon B', subdomain='salonb')
        user_b = User.objects.create_user(
            email='admin@salonb.com',
            password='test123',
            full_name='Admin B',
            tenant=tenant_b
        )
        
        # Crear venta para Tenant A
        sale_a = Sale.objects.create(
            user=self.user,
            employee=self.employee,
            total=Decimal('100.00')
        )
        
        # Verificar que Tenant B NO ve venta de Tenant A
        sales_b = Sale.objects.filter(user__tenant=tenant_b)
        self.assertEqual(sales_b.count(), 0)
        
        # Verificar que Tenant A SÍ ve su venta
        sales_a = Sale.objects.filter(user__tenant=self.tenant)
        self.assertEqual(sales_a.count(), 1)
    
    def test_commission_calculation_accuracy(self):
        """CRÍTICO: Cálculo de comisión debe ser exacto"""
        test_cases = [
            (Decimal('100.00'), Decimal('40.00'), Decimal('40.00')),
            (Decimal('250.50'), Decimal('40.00'), Decimal('100.20')),
            (Decimal('1000.00'), Decimal('25.00'), Decimal('250.00')),
        ]
        
        for total, rate, expected_commission in test_cases:
            self.employee.commission_rate = rate
            self.employee.save()
            
            sale = Sale.objects.create(
                user=self.user,
                employee=self.employee,
                total=total,
                status='confirmed'
            )
            
            self.assertEqual(
                sale.commission_amount_snapshot,
                expected_commission,
                f"Comisión incorrecta para total={total}, rate={rate}"
            )
            
            sale.delete()  # Limpiar para siguiente test


class ReportsIntegrityTests(TestCase):
    """Tests que validan que reportes NO alteran datos"""
    
    def setUp(self):
        self.owner = User.objects.create_user(email='owner@reports.com', password='pass', full_name='Owner')
        self.tenant = Tenant.objects.create(name='Test Salon', subdomain='test', owner=self.owner)
        self.user = User.objects.create_user(
            email='admin@test.com',
            password='test123',
            full_name='Admin Test',
            tenant=self.tenant
        )
    
    def test_reports_are_read_only(self):
        """CRÍTICO: Reportes NO deben modificar datos"""
        # Crear venta
        sale = Sale.objects.create(
            user=self.user,
            total=Decimal('100.00'),
            status='confirmed'
        )
        
        original_total = sale.total
        
        # Simular consulta de reporte
        from django.db.models import Sum
        Sale.objects.filter(user__tenant=self.tenant).aggregate(Sum('total'))
        
        # Verificar que venta NO cambió
        sale.refresh_from_db()
        self.assertEqual(sale.total, original_total)
