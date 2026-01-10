"""
Tests de integración críticos para validar sistema completo
"""
import pytest
from django.test import TestCase, TransactionTestCase
from django.db import connection
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from apps.tenants_api.models import Tenant
from apps.employees_api.models import Employee
from apps.payroll_api.models import PayrollPeriod, PayrollCalculation, PayrollPaymentNew
from apps.payroll_api.calculation_engine import PayrollService, PayrollCalculationEngine
from apps.employees_api.earnings_models import Earning
import structlog

User = get_user_model()
logger = structlog.get_logger("apps.payroll_api")

class RLSIntegrationTest(TransactionTestCase):
    """
    CRÍTICO: Validar aislamiento cross-tenant con RLS
    """
    
    def setUp(self):
        # Tenant 1
        self.owner1 = User.objects.create_user(email="owner1@test.com", password="pass")
        self.tenant1 = Tenant.objects.create(name="Salon 1", subdomain="salon1", owner=self.owner1)
        self.owner1.tenant = self.tenant1
        self.owner1.save()
        
        self.employee1 = Employee.objects.create(
            user=User.objects.create_user(email="emp1@test.com", password="pass", tenant=self.tenant1),
            tenant=self.tenant1,
            salary_type='commission',
            commission_percentage=Decimal('40.00'),
            payment_frequency='biweekly'
        )
        
        # Tenant 2
        self.owner2 = User.objects.create_user(email="owner2@test.com", password="pass")
        self.tenant2 = Tenant.objects.create(name="Salon 2", subdomain="salon2", owner=self.owner2)
        self.owner2.tenant = self.tenant2
        self.owner2.save()
        
        self.employee2 = Employee.objects.create(
            user=User.objects.create_user(email="emp2@test.com", password="pass", tenant=self.tenant2),
            tenant=self.tenant2,
            salary_type='commission',
            commission_percentage=Decimal('35.00'),
            payment_frequency='biweekly'
        )
    
    def test_rls_tenant_isolation_employees(self):
        """Verificar que RLS aísla empleados por tenant"""
        # Sin contexto (SuperAdmin) - ve todos
        all_employees = Employee.objects.all().count()
        self.assertEqual(all_employees, 2)
        
        # Con contexto tenant1 - solo ve empleados de tenant1
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", [str(self.tenant1.id)])
            
            tenant1_employees = Employee.objects.all()
            self.assertEqual(tenant1_employees.count(), 1)
            self.assertEqual(tenant1_employees.first().id, self.employee1.id)
            
            # Verificar que NO puede ver employee2
            with self.assertRaises(Employee.DoesNotExist):
                Employee.objects.get(id=self.employee2.id)
            
            cursor.execute("SELECT set_config('app.current_tenant_id', '0', false)")
    
    def test_rls_payroll_calculations_isolation(self):
        """Verificar aislamiento de cálculos de nómina"""
        # Crear períodos y cálculos para ambos tenants
        period1 = PayrollPeriod.objects.create(
            tenant=self.tenant1,
            frequency='biweekly',
            period_start=timezone.now().date(),
            period_end=timezone.now().date(),
            period_year=2024,
            period_index=1
        )
        
        period2 = PayrollPeriod.objects.create(
            tenant=self.tenant2,
            frequency='biweekly',
            period_start=timezone.now().date(),
            period_end=timezone.now().date(),
            period_year=2024,
            period_index=1
        )
        
        calc1 = PayrollService.calculate_payroll(self.employee1, period1)
        calc2 = PayrollService.calculate_payroll(self.employee2, period2)
        
        # Sin contexto - ve todos
        all_calculations = PayrollCalculation.objects.all().count()
        self.assertEqual(all_calculations, 2)
        
        # Con contexto tenant1 - solo ve cálculos de tenant1
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", [str(self.tenant1.id)])
            
            tenant1_calculations = PayrollCalculation.objects.all()
            self.assertEqual(tenant1_calculations.count(), 1)
            self.assertEqual(tenant1_calculations.first().id, calc1.id)
            
            cursor.execute("SELECT set_config('app.current_tenant_id', '0', false)")

class PayrollCalculationIntegrationTest(TestCase):
    """
    CRÍTICO: Validar cálculos correctos y reproducibles
    """
    
    def setUp(self):
        self.owner = User.objects.create_user(email="owner@test.com", password="pass")
        self.tenant = Tenant.objects.create(name="Test Salon", subdomain="test", owner=self.owner)
        self.owner.tenant = self.tenant
        self.owner.save()
        
        self.period = PayrollPeriod.objects.create(
            tenant=self.tenant,
            frequency='biweekly',
            period_start=timezone.now().date().replace(day=1),
            period_end=timezone.now().date().replace(day=15),
            period_year=2024,
            period_index=1
        )
    
    def test_commission_calculation_deterministic(self):
        """Verificar que cálculos de comisión son deterministas"""
        employee = Employee.objects.create(
            user=User.objects.create_user(email="emp@test.com", password="pass", tenant=self.tenant),
            tenant=self.tenant,
            salary_type='commission',
            commission_percentage=Decimal('40.00'),
            payment_frequency='biweekly'
        )
        
        # Crear earnings conocidos
        Earning.objects.create(
            employee=employee,
            amount=Decimal('1000.00'),
            service_name='Corte',
            date_earned=timezone.now().replace(day=5)
        )
        Earning.objects.create(
            employee=employee,
            amount=Decimal('2000.00'),
            service_name='Tinte',
            date_earned=timezone.now().replace(day=10)
        )
        
        # Calcular múltiples veces - debe ser idéntico
        calc1 = PayrollService.calculate_payroll(employee, self.period)
        calc2 = PayrollService.calculate_payroll(employee, self.period)
        
        # Verificar que los cálculos son idénticos
        self.assertEqual(calc1.commission_total, calc2.commission_total)
        self.assertEqual(calc1.gross_total, calc2.gross_total)
        self.assertEqual(calc1.net_amount, calc2.net_amount)
        
        # Verificar valores esperados
        expected_commission = Decimal('3000.00') * Decimal('0.40')  # 1200.00
        self.assertEqual(calc1.commission_total, expected_commission)
        self.assertEqual(calc1.gross_total, expected_commission)
        self.assertEqual(calc1.net_amount, expected_commission)  # Sin deducciones
    
    def test_mixed_salary_calculation_with_deductions(self):
        """Verificar cálculo mixto con deducciones legales"""
        employee = Employee.objects.create(
            user=User.objects.create_user(email="mixed@test.com", password="pass", tenant=self.tenant),
            tenant=self.tenant,
            salary_type='mixed',
            contractual_monthly_salary=Decimal('30000.00'),
            commission_percentage=Decimal('25.00'),
            payment_frequency='biweekly',
            apply_afp=True,
            apply_sfs=True
        )
        
        # Crear earning
        Earning.objects.create(
            employee=employee,
            amount=Decimal('4000.00'),
            service_name='Servicio Premium',
            date_earned=timezone.now().replace(day=15)
        )
        
        # Modificar período para ser última quincena (aplicar deducciones)
        self.period.period_start = timezone.now().date().replace(day=16)
        self.period.period_end = timezone.now().date().replace(day=28)
        self.period.save()
        
        calculation = PayrollService.calculate_payroll(employee, self.period)
        
        # Verificar cálculos
        expected_base = Decimal('15000.00')  # 30000/2
        expected_commission = Decimal('4000.00') * Decimal('0.25')  # 1000.00
        expected_gross = expected_base + expected_commission  # 16000.00
        
        # Deducciones legales (solo en última quincena)
        expected_afp = expected_gross * Decimal('0.0287')  # 459.20
        expected_sfs = expected_gross * Decimal('0.0304')  # 486.40
        expected_legal_deductions = expected_afp + expected_sfs  # 945.60
        expected_net = expected_gross - expected_legal_deductions  # 15054.40
        
        self.assertEqual(calculation.base_salary, expected_base)
        self.assertEqual(calculation.commission_total, expected_commission)
        self.assertEqual(calculation.gross_total, expected_gross)
        self.assertEqual(calculation.legal_deductions, expected_legal_deductions)
        self.assertEqual(calculation.net_amount, expected_net)
    
    def test_calculation_versioning(self):
        """Verificar versionado de cálculos"""
        employee = Employee.objects.create(
            user=User.objects.create_user(email="version@test.com", password="pass", tenant=self.tenant),
            tenant=self.tenant,
            salary_type='fixed',
            contractual_monthly_salary=Decimal('40000.00'),
            payment_frequency='biweekly'
        )
        
        # Primera calculación
        calc1 = PayrollService.calculate_payroll(employee, self.period)
        self.assertEqual(calc1.version, 1)
        self.assertTrue(calc1.is_current)
        
        # Segunda calculación (recálculo)
        calc2 = PayrollService.calculate_payroll(employee, self.period)
        self.assertEqual(calc2.version, 2)
        self.assertTrue(calc2.is_current)
        
        # Verificar que la primera ya no es current
        calc1.refresh_from_db()
        self.assertFalse(calc1.is_current)
    
    def test_calculation_breakdown_auditability(self):
        """Verificar que breakdown es completamente auditable"""
        employee = Employee.objects.create(
            user=User.objects.create_user(email="audit@test.com", password="pass", tenant=self.tenant),
            tenant=self.tenant,
            salary_type='commission',
            commission_percentage=Decimal('30.00'),
            payment_frequency='biweekly'
        )
        
        # Crear earnings con detalles específicos
        earning1 = Earning.objects.create(
            employee=employee,
            amount=Decimal('1500.00'),
            service_name='Corte Premium',
            date_earned=timezone.now().replace(day=3)
        )
        earning2 = Earning.objects.create(
            employee=employee,
            amount=Decimal('2500.00'),
            service_name='Tratamiento Capilar',
            date_earned=timezone.now().replace(day=8)
        )
        
        calculation = PayrollService.calculate_payroll(employee, self.period)
        breakdown = calculation.calculation_breakdown
        
        # Verificar estructura completa del breakdown
        self.assertIn('calculation_metadata', breakdown)
        self.assertIn('base_salary', breakdown)
        self.assertIn('commissions', breakdown)
        self.assertIn('gross_total', breakdown)
        
        # Verificar metadatos
        metadata = breakdown['calculation_metadata']
        self.assertEqual(metadata['employee_id'], employee.id)
        self.assertEqual(metadata['salary_type'], 'commission')
        
        # Verificar detalle de comisiones
        commission_details = breakdown['commissions']['details']
        self.assertEqual(len(commission_details), 2)
        
        # Verificar trazabilidad de cada earning
        detail1 = next(d for d in commission_details if d['earning_id'] == earning1.id)
        self.assertEqual(detail1['service_name'], 'Corte Premium')
        self.assertEqual(detail1['earning_amount'], '1500.00')
        self.assertEqual(detail1['commission_amount'], '450.00')  # 1500 * 0.30

class LoggingIntegrationTest(TestCase):
    """
    CRÍTICO: Verificar que logging estructurado funciona
    """
    
    def setUp(self):
        self.owner = User.objects.create_user(email="log@test.com", password="pass")
        self.tenant = Tenant.objects.create(name="Log Salon", subdomain="log", owner=self.owner)
        
    def test_structured_logging_payroll(self):
        """Verificar que logs estructurados se generan correctamente"""
        with self.assertLogs('apps.payroll_api', level='INFO') as log_context:
            employee = Employee.objects.create(
                user=User.objects.create_user(email="emp@log.com", password="pass", tenant=self.tenant),
                tenant=self.tenant,
                salary_type='fixed',
                contractual_monthly_salary=Decimal('25000.00'),
                payment_frequency='biweekly'
            )
            
            period = PayrollPeriod.objects.create(
                tenant=self.tenant,
                frequency='biweekly',
                period_start=timezone.now().date(),
                period_end=timezone.now().date(),
                period_year=2024,
                period_index=1
            )
            
            PayrollService.calculate_payroll(employee, period)
        
        # Verificar que se generaron logs
        self.assertTrue(len(log_context.output) > 0)
        
        # Verificar que contienen información estructurada
        log_messages = ' '.join(log_context.output)
        self.assertIn('payroll_calculation', log_messages)
        self.assertIn('employee_id', log_messages)

class PaymentIntegrationTest(TestCase):
    """
    CRÍTICO: Verificar flujo completo de pagos
    """
    
    def setUp(self):
        self.owner = User.objects.create_user(email="pay@test.com", password="pass")
        self.tenant = Tenant.objects.create(name="Pay Salon", subdomain="pay", owner=self.owner)
        self.owner.tenant = self.tenant
        self.owner.save()
        
        self.employee = Employee.objects.create(
            user=User.objects.create_user(email="emp@pay.com", password="pass", tenant=self.tenant),
            tenant=self.tenant,
            salary_type='fixed',
            contractual_monthly_salary=Decimal('20000.00'),
            payment_frequency='biweekly'
        )
        
        self.period = PayrollPeriod.objects.create(
            tenant=self.tenant,
            frequency='biweekly',
            period_start=timezone.now().date(),
            period_end=timezone.now().date(),
            period_year=2024,
            period_index=1
        )
    
    def test_complete_payment_flow(self):
        """Verificar flujo completo: Cálculo → Pago → Auditoría"""
        # 1. Calcular nómina
        calculation = PayrollService.calculate_payroll(self.employee, self.period)
        self.assertEqual(calculation.base_salary, Decimal('10000.00'))  # 20000/2
        
        # 2. Ejecutar pago
        payment = PayrollService.execute_payment(
            calculation=calculation,
            paid_by=self.owner,
            payment_method='bank_transfer',
            payment_reference='TXN123456'
        )
        
        # 3. Verificar pago
        self.assertEqual(payment.amount_paid, calculation.net_amount)
        self.assertEqual(payment.payment_method, 'bank_transfer')
        self.assertEqual(payment.payment_reference, 'TXN123456')
        self.assertEqual(payment.paid_by, self.owner)
        
        # 4. Verificar que no se puede pagar dos veces
        with self.assertRaises(ValueError):
            PayrollService.execute_payment(calculation, self.owner)
        
        # 5. Verificar trazabilidad
        self.assertEqual(payment.calculation, calculation)
        self.assertEqual(payment.tenant, self.tenant)
        self.assertIsNotNone(payment.paid_at)