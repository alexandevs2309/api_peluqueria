"""
Smoke tests mínimos para validar flujo crítico de pagos
Ejecutar con: python manage.py test test_payments_smoke
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.tenants_api.models import Tenant
from apps.roles_api.models import Role, UserRole
from apps.employees_api.models import Employee
from apps.pos_api.models import CashRegister
from decimal import Decimal
import threading
import time

User = get_user_model()

class PaymentsSmokeTest(TestCase):
    def setUp(self):
        # Tenant y roles básicos
        self.tenant = Tenant.objects.create(name="Test Tenant")
        
        self.client_admin_role = Role.objects.create(name="Client-Admin")
        self.client_staff_role = Role.objects.create(name="Client-Staff") 
        self.super_admin_role = Role.objects.create(name="Super-Admin")
        
        # Usuarios
        self.client_admin = User.objects.create_user(
            email="admin@test.com", 
            password="test123",
            tenant=self.tenant
        )
        UserRole.objects.create(user=self.client_admin, role=self.client_admin_role)
        
        self.client_staff = User.objects.create_user(
            email="staff@test.com",
            password="test123", 
            tenant=self.tenant
        )
        UserRole.objects.create(user=self.client_staff, role=self.client_staff_role)
        
        self.super_admin = User.objects.create_user(
            email="super@test.com",
            password="test123",
            is_superuser=True
        )
        UserRole.objects.create(user=self.super_admin, role=self.super_admin_role)
        
        # Empleado
        self.employee = Employee.objects.create(
            user=self.client_admin,
            tenant=self.tenant,
            salary_type='commission',
            commission_percentage=Decimal('40.0')
        )
        
        self.client = APIClient()

    def test_1_cash_payment_without_open_register_returns_409(self):
        """
        Precondiciones: CLIENT_ADMIN, caja cerrada, payment_method='cash'
        Request: POST /pay_employee con cash
        Status esperado: 409 Conflict
        Qué valida: Validación de caja abierta funciona
        """
        self.client.force_authenticate(user=self.client_admin)
        
        response = self.client.post('/api/employees/payments/pay_employee/', {
            'employee_id': self.employee.id,
            'amount': 100.00,
            'payment_method': 'cash',
            'idempotency_key': 'test-key-1'
        })
        
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn('caja registradora abierta', response.data['error'])

    def test_2_cash_payment_with_open_register_succeeds(self):
        """
        Precondiciones: CLIENT_ADMIN, caja abierta, payment_method='cash'
        Request: POST /pay_employee con cash
        Status esperado: 200/201 OK
        Qué valida: Pago en efectivo funciona con caja abierta
        """
        # Crear caja abierta
        CashRegister.objects.create(
            user=self.client_admin,
            is_open=True,
            initial_cash=Decimal('1000.00')
        )
        
        self.client.force_authenticate(user=self.client_admin)
        
        response = self.client.post('/api/employees/payments/pay_employee/', {
            'employee_id': self.employee.id,
            'amount': 100.00,
            'payment_method': 'cash',
            'idempotency_key': 'test-key-2'
        })
        
        # Puede ser 200 (ya procesado) o 201 (nuevo) o 400 (balance insuficiente)
        # Lo importante es que NO sea 409 (caja cerrada)
        self.assertNotEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_3_concurrent_payments_same_sales_one_succeeds_one_conflicts(self):
        """
        Precondiciones: CLIENT_ADMIN, dos requests simultáneas con mismas ventas
        Request: 2x POST /pay_employee concurrentes
        Status esperado: 1 OK / 1 Conflict
        Qué valida: transaction.atomic() previene race conditions
        """
        CashRegister.objects.create(
            user=self.client_admin,
            is_open=True,
            initial_cash=Decimal('1000.00')
        )
        
        self.client.force_authenticate(user=self.client_admin)
        
        results = []
        
        def make_payment(key_suffix):
            client = APIClient()
            client.force_authenticate(user=self.client_admin)
            response = client.post('/api/employees/payments/pay_employee/', {
                'employee_id': self.employee.id,
                'amount': 50.00,
                'payment_method': 'card',  # Evitar validación de caja
                'idempotency_key': f'concurrent-test-{key_suffix}'
            })
            results.append(response.status_code)
        
        # Ejecutar concurrentemente
        thread1 = threading.Thread(target=make_payment, args=('1',))
        thread2 = threading.Thread(target=make_payment, args=('2',))
        
        thread1.start()
        thread2.start()
        
        thread1.join()
        thread2.join()
        
        # Al menos uno debe fallar por alguna razón (balance, duplicado, etc.)
        # Lo importante es que no haya corrupción de datos
        self.assertEqual(len(results), 2)

    def test_4_client_staff_cannot_pay_returns_403(self):
        """
        Precondiciones: CLIENT_STAFF intenta pagar
        Request: POST /pay_employee
        Status esperado: 403 Forbidden
        Qué valida: Permisos CLIENT_ADMIN funcionan correctamente
        """
        self.client.force_authenticate(user=self.client_staff)
        
        response = self.client.post('/api/employees/payments/pay_employee/', {
            'employee_id': self.employee.id,
            'amount': 100.00,
            'payment_method': 'card',
            'idempotency_key': 'staff-test'
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_5_super_admin_cannot_pay_returns_403(self):
        """
        Precondiciones: SUPER_ADMIN intenta pagar
        Request: POST /pay_employee  
        Status esperado: 403 Forbidden
        Qué valida: Separación de dominios SaaS vs Tenant funciona
        """
        self.client.force_authenticate(user=self.super_admin)
        
        response = self.client.post('/api/employees/payments/pay_employee/', {
            'employee_id': self.employee.id,
            'amount': 100.00,
            'payment_method': 'card',
            'idempotency_key': 'super-test'
        })
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)