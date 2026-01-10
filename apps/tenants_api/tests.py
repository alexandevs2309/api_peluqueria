"""
Test básico para verificar Row Level Security
"""
import pytest
from django.test import TestCase
from django.db import connection
from django.contrib.auth import get_user_model
from apps.tenants_api.models import Tenant

User = get_user_model()

class RLSTestCase(TestCase):
    
    def setUp(self):
        # Crear tenants de prueba
        self.owner1 = User.objects.create_user(email="owner1@test.com", password="pass")
        self.owner2 = User.objects.create_user(email="owner2@test.com", password="pass")
        
        self.tenant1 = Tenant.objects.create(
            name="Salon 1",
            subdomain="salon1",
            owner=self.owner1
        )
        
        self.tenant2 = Tenant.objects.create(
            name="Salon 2", 
            subdomain="salon2",
            owner=self.owner2
        )
        
        # Asignar tenants a usuarios
        self.owner1.tenant = self.tenant1
        self.owner1.save()
        
        self.owner2.tenant = self.tenant2
        self.owner2.save()
    
    def test_rls_function_exists(self):
        """Verificar que la función RLS existe"""
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_tenant_id()")
            result = cursor.fetchone()
            self.assertEqual(result[0], 0)  # Default sin contexto
    
    def test_rls_context_setting(self):
        """Verificar que se puede establecer contexto de tenant"""
        with connection.cursor() as cursor:
            # Establecer contexto
            cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", [str(self.tenant1.id)])
            
            # Verificar contexto
            cursor.execute("SELECT current_tenant_id()")
            result = cursor.fetchone()
            self.assertEqual(result[0], self.tenant1.id)
            
            # Limpiar contexto
            cursor.execute("SELECT set_config('app.current_tenant_id', '0', false)")
    
    def test_tenant_isolation(self):
        """Verificar aislamiento básico de tenants"""
        # Sin contexto, debería ver todos los tenants (SuperAdmin)
        all_tenants = Tenant.objects.all().count()
        self.assertEqual(all_tenants, 2)
        
        # Con contexto de tenant1, solo debería ver tenant1
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", [str(self.tenant1.id)])
            
            # Verificar que RLS está activo
            tenant_count = Tenant.objects.all().count()
            self.assertEqual(tenant_count, 1)
            
            # Verificar que es el tenant correcto
            visible_tenant = Tenant.objects.first()
            self.assertEqual(visible_tenant.id, self.tenant1.id)
            
            # Limpiar contexto
            cursor.execute("SELECT set_config('app.current_tenant_id', '0', false)")
    
    def test_user_isolation(self):
        """Verificar aislamiento de usuarios por tenant"""
        # Crear usuarios adicionales
        user1 = User.objects.create_user(
            email="user1@test.com",
            password="pass",
            tenant=self.tenant1
        )
        
        user2 = User.objects.create_user(
            email="user2@test.com", 
            password="pass",
            tenant=self.tenant2
        )
        
        # Sin contexto (SuperAdmin), ver todos
        all_users = User.objects.filter(tenant__isnull=False).count()
        self.assertEqual(all_users, 4)  # 2 owners + 2 users
        
        # Con contexto tenant1
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.current_tenant_id', %s, false)", [str(self.tenant1.id)])
            
            tenant1_users = User.objects.filter(tenant__isnull=False).count()
            self.assertEqual(tenant1_users, 2)  # owner1 + user1
            
            # Verificar que son los usuarios correctos
            visible_users = User.objects.filter(tenant__isnull=False).values_list('email', flat=True)
            self.assertIn('owner1@test.com', visible_users)
            self.assertIn('user1@test.com', visible_users)
            self.assertNotIn('owner2@test.com', visible_users)
            self.assertNotIn('user2@test.com', visible_users)
            
            # Limpiar contexto
            cursor.execute("SELECT set_config('app.current_tenant_id', '0', false)")