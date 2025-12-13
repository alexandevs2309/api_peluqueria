import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta

from apps.tenants_api.models import Tenant
from apps.employees_api.models import Employee
from apps.employees_api.earnings_models import PayrollBatch, PayrollBatchItem, Earning
from apps.pos_api.models import Sale
from apps.employees_api.tasks import create_earning_from_sale, process_payroll_batch_task

User = get_user_model()

class PayrollBatchTestCase(TestCase):
    
    def setUp(self):
        # Crear usuario owner primero
        self.owner_user = User.objects.create_user(
            email="owner@test.com",
            password="testpass123",
            is_staff=True
        )
        
        # Crear tenant
        self.tenant = Tenant.objects.create(
            name="Test Salon",
            subdomain="test",
            is_active=True,
            owner=self.owner_user
        )
        
        # Crear usuario admin
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            tenant=self.tenant,
            is_staff=True
        )
        
        # Crear empleado
        self.employee_user = User.objects.create_user(
            email="employee@test.com",
            password="testpass123",
            tenant=self.tenant
        )
        
        self.employee = Employee.objects.create(
            user=self.employee_user,
            tenant=self.tenant,
            salary_type='commission',
            commission_percentage=Decimal('40.00'),
            is_active=True
        )
    
    def test_payroll_batch_creation(self):
        """Test creación de lote de nómina"""
        batch = PayrollBatch.objects.create(
            tenant=self.tenant,
            period_start=date.today() - timedelta(days=15),
            period_end=date.today(),
            frequency='biweekly',
            created_by=self.admin_user
        )
        
        self.assertIsNotNone(batch.batch_number)
        self.assertEqual(batch.status, 'draft')
        self.assertEqual(batch.tenant, self.tenant)
    
    def test_payroll_batch_item_creation(self):
        """Test creación de items de lote"""
        batch = PayrollBatch.objects.create(
            tenant=self.tenant,
            period_start=date.today() - timedelta(days=15),
            period_end=date.today(),
            frequency='biweekly',
            created_by=self.admin_user
        )
        
        item = PayrollBatchItem.objects.create(
            batch=batch,
            employee=self.employee,
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('1000.00')
        )
        
        self.assertEqual(item.status, 'pending')
        self.assertEqual(item.deductions, Decimal('0.00'))
        self.assertEqual(batch.items.count(), 1)
    
    def test_idempotent_earning_creation(self):
        """Test creación idempotente de earnings desde venta"""
        # Crear venta
        sale = Sale.objects.create(
            employee=self.employee,
            total=Decimal('100.00'),
            status='completed',
            date_time=timezone.now()
        )
        
        external_id = f"sale-{sale.id}-test"
        
        # Primera ejecución
        result1 = create_earning_from_sale(sale.id, external_id)
        self.assertEqual(result1['status'], 'created')
        
        # Segunda ejecución (debe ser idempotente)
        result2 = create_earning_from_sale(sale.id, external_id)
        self.assertEqual(result2['status'], 'exists')
        
        # Verificar que solo existe un earning
        earnings_count = Earning.objects.filter(external_id=external_id).count()
        self.assertEqual(earnings_count, 1)
    
    def test_earning_calculation_commission(self):
        """Test cálculo de earning por comisión"""
        sale = Sale.objects.create(
            employee=self.employee,
            total=Decimal('100.00'),
            status='completed',
            date_time=timezone.now()
        )
        
        external_id = f"sale-{sale.id}-test"
        result = create_earning_from_sale(sale.id, external_id)
        
        self.assertEqual(result['status'], 'created')
        # 40% de 100 = 40
        self.assertEqual(result['amount'], 40.0)
        
        earning = Earning.objects.get(external_id=external_id)
        self.assertEqual(earning.amount, Decimal('40.00'))
        self.assertEqual(earning.earning_type, 'commission')
    
    def test_earning_fixed_salary_skip(self):
        """Test que empleados con sueldo fijo no generan earnings por venta"""
        # Cambiar empleado a sueldo fijo
        self.employee.salary_type = 'fixed'
        self.employee.salary_amount = Decimal('1200.00')
        self.employee.save()
        
        sale = Sale.objects.create(
            employee=self.employee,
            total=Decimal('100.00'),
            status='completed',
            date_time=timezone.now()
        )
        
        external_id = f"sale-{sale.id}-test"
        result = create_earning_from_sale(sale.id, external_id)
        
        self.assertEqual(result['status'], 'skipped')
        self.assertEqual(result['reason'], 'zero_amount_or_fixed_salary')
    
    def test_process_payroll_batch_task(self):
        """Test procesamiento de lote de nómina"""
        # Crear batch con items
        batch = PayrollBatch.objects.create(
            tenant=self.tenant,
            period_start=date.today() - timedelta(days=15),
            period_end=date.today(),
            frequency='biweekly',
            created_by=self.admin_user,
            status='approved'
        )
        
        item = PayrollBatchItem.objects.create(
            batch=batch,
            employee=self.employee,
            gross_amount=Decimal('1000.00'),
            net_amount=Decimal('1000.00')
        )
        
        # Procesar batch
        result = process_payroll_batch_task(batch.id)
        
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(result['processed_count'], 1)
        self.assertEqual(result['failed_count'], 0)
        
        # Verificar que item fue marcado como pagado
        item.refresh_from_db()
        self.assertEqual(item.status, 'paid')
        self.assertIsNotNone(item.external_ref)
        self.assertIsNotNone(item.processed_at)
        
        # Verificar que batch fue completado
        batch.refresh_from_db()
        self.assertEqual(batch.status, 'completed')
        self.assertIsNotNone(batch.processed_at)

class PayrollBatchAPITestCase(TestCase):
    
    def setUp(self):
        # Crear usuario owner primero
        self.owner_user = User.objects.create_user(
            email="owner@test.com",
            password="testpass123",
            is_staff=True
        )
        
        self.tenant = Tenant.objects.create(
            name="Test Salon",
            subdomain="test",
            is_active=True,
            owner=self.owner_user
        )
        
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass123",
            tenant=self.tenant,
            is_staff=True
        )
        
        self.client.force_login(self.admin_user)
    
    def test_export_pdf_endpoint(self):
        """Test endpoint de exportación PDF"""
        batch = PayrollBatch.objects.create(
            tenant=self.tenant,
            period_start=date.today() - timedelta(days=15),
            period_end=date.today(),
            frequency='biweekly',
            created_by=self.admin_user
        )
        
        response = self.client.get(f'/api/employees/earnings/export_payroll_pdf/?batch_id={batch.id}')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])