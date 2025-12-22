"""
Tests mínimos de regresión para consistencia de estados POS
FASE 2: Validar que no se rompió funcionalidad existente
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Sale, CashRegister
from .state_validators import SaleStateValidator
from apps.tenants_api.models import Tenant

User = get_user_model()

class SaleStateConsistencyTest(TestCase):
    """Tests críticos de consistencia de estados"""
    
    def setUp(self):
        # Crear usuario owner primero
        self.owner = User.objects.create_user(
            email="owner@test.com",
            password="test123"
        )
        self.tenant = Tenant.objects.create(
            name="Test Tenant",
            owner=self.owner
        )
        self.user = User.objects.create_user(
            email="test@test.com",
            password="test123",
            tenant=self.tenant
        )
    
    def test_sale_creation_basic(self):
        """Test básico: crear venta no rompe funcionalidad"""
        sale = Sale.objects.create(
            user=self.user,
            total=Decimal('100.00'),
            status='completed'
        )
        self.assertEqual(sale.status, 'completed')
        self.assertFalse(sale.earnings_generated)
        self.assertFalse(sale.earnings_reverted)
    
    def test_valid_state_transitions(self):
        """Test: transiciones válidas funcionan"""
        sale = Sale.objects.create(
            user=self.user,
            total=Decimal('100.00'),
            status='pending'
        )
        
        # pending → completed (válida)
        sale.status = 'completed'
        sale.save()  # No debe lanzar excepción
        
        # completed → refunded (válida)
        sale.status = 'refunded'
        sale.save()  # No debe lanzar excepción
        self.assertTrue(sale.closed)  # Auto-cerrada
    
    def test_invalid_state_transitions(self):
        """Test: transiciones inválidas son bloqueadas"""
        sale = Sale.objects.create(
            user=self.user,
            total=Decimal('100.00'),
            status='refunded',
            closed=True
        )
        
        # refunded → completed (inválida)
        sale.status = 'completed'
        with self.assertRaises(ValidationError):
            sale.save()
    
    def test_state_consistency_validation(self):
        """Test: consistencia entre status y closed"""
        # Estado refunded debe estar cerrado
        with self.assertRaises(ValidationError):
            sale = Sale(
                user=self.user,
                total=Decimal('100.00'),
                status='refunded',
                closed=False  # Inconsistente
            )
            sale.clean()
    
    def test_earnings_tracking(self):
        """Test: tracking de earnings funciona"""
        sale = Sale.objects.create(
            user=self.user,
            total=Decimal('100.00'),
            status='completed'
        )
        
        # Puede generar earnings
        self.assertTrue(sale.can_generate_earnings)
        
        # Marcar como generado
        sale.mark_earnings_generated()
        sale.refresh_from_db()
        self.assertTrue(sale.earnings_generated)
        self.assertFalse(sale.can_generate_earnings)  # Ya no puede
    
    def test_cash_register_state_validation(self):
        """Test: validación de estados de caja"""
        register = CashRegister.objects.create(
            user=self.user,
            initial_cash=Decimal('100.00')
        )
        
        # Caja abierta permite operaciones
        self.assertTrue(register.is_open)
        
        # Cerrar caja
        register.is_open = False
        register.save()
        
        # Validar que no se puede operar
        from .state_validators import CashRegisterStateValidator
        with self.assertRaises(ValidationError):
            CashRegisterStateValidator.validate_open_operation(register)

class PosApiRegressionTest(TestCase):
    """Tests de regresión para funcionalidad existente"""
    
    def setUp(self):
        # Crear usuario owner primero
        self.owner = User.objects.create_user(
            email="owner2@test.com",
            password="test123"
        )
        self.tenant = Tenant.objects.create(
            name="Test Tenant 2",
            owner=self.owner
        )
        self.user = User.objects.create_user(
            email="test2@test.com",
            password="test123",
            tenant=self.tenant
        )
    
    def test_existing_sale_fields_preserved(self):
        """Test: campos existentes siguen funcionando"""
        sale = Sale.objects.create(
            user=self.user,
            total=Decimal('100.00'),
            discount=Decimal('10.00'),
            paid=Decimal('90.00'),
            payment_method='cash',
            status='completed'
        )
        
        # Campos originales intactos
        self.assertEqual(sale.total, Decimal('100.00'))
        self.assertEqual(sale.discount, Decimal('10.00'))
        self.assertEqual(sale.paid, Decimal('90.00'))
        self.assertEqual(sale.payment_method, 'cash')
    
    def test_cash_register_functionality_preserved(self):
        """Test: funcionalidad de caja preservada"""
        register = CashRegister.objects.create(
            user=self.user,
            initial_cash=Decimal('100.00')
        )
        
        # Propiedades calculadas funcionan
        self.assertEqual(register.display_amount, 100.00)
        self.assertTrue(register.is_open)
    
    def test_sale_properties_work(self):
        """Test: propiedades de venta funcionan"""
        sale = Sale.objects.create(
            user=self.user,
            total=Decimal('100.00'),
            status='completed'
        )
        
        # Nuevas propiedades
        self.assertTrue(sale.can_be_edited)
        self.assertTrue(sale.can_generate_earnings)
        
        # Cambiar a estado final
        sale.status = 'refunded'
        sale.save()
        self.assertFalse(sale.can_be_edited)