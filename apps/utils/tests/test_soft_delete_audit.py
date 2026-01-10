"""
Tests críticos para soft delete y auditoría
apps/utils/tests/test_soft_delete_audit.py
"""
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.db import connection
from apps.audit_api.audit_models import BusinessAuditLog, AuditAction
from apps.utils.models import BusinessModel


User = get_user_model()


class SoftDeleteTestCase(TestCase):
    """Tests críticos para soft delete."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant_id=1
        )
    
    def test_soft_delete_no_elimina_datos(self):
        """Verificar que soft delete NO elimina datos físicamente."""
        # Crear registro de prueba (usando cualquier modelo con BusinessModel)
        from apps.clients_api.models import Client
        
        client = Client.objects.create(
            name='Test Client',
            email='client@test.com',
            tenant_id=1
        )
        client_id = client.id
        
        # Soft delete
        client.soft_delete(user=self.user)
        
        # Verificar que el registro existe físicamente
        deleted_client = Client.all_objects.get(id=client_id)
        self.assertTrue(deleted_client.is_deleted)
        self.assertIsNotNone(deleted_client.deleted_at)
        self.assertEqual(deleted_client.deleted_by, self.user)
        
        # Verificar que NO aparece en queryset por defecto
        with self.assertRaises(Client.DoesNotExist):
            Client.objects.get(id=client_id)
    
    def test_manager_excluye_soft_deleted(self):
        """Verificar que manager por defecto excluye soft-deleted."""
        from apps.clients_api.models import Client
        
        # Crear 3 clientes
        client1 = Client.objects.create(name='Client 1', tenant_id=1)
        client2 = Client.objects.create(name='Client 2', tenant_id=1)
        client3 = Client.objects.create(name='Client 3', tenant_id=1)
        
        # Soft delete uno
        client2.soft_delete(user=self.user)
        
        # Manager por defecto debe mostrar solo 2
        active_clients = Client.objects.all()
        self.assertEqual(active_clients.count(), 2)
        self.assertIn(client1, active_clients)
        self.assertIn(client3, active_clients)
        self.assertNotIn(client2, active_clients)
        
        # all_objects debe mostrar los 3
        all_clients = Client.all_objects.all()
        self.assertEqual(all_clients.count(), 3)
    
    def test_restore_funciona_correctamente(self):
        """Verificar que restore funciona."""
        from apps.clients_api.models import Client
        
        client = Client.objects.create(name='Test Client', tenant_id=1)
        
        # Soft delete
        client.soft_delete(user=self.user)
        self.assertTrue(client.is_deleted)
        
        # Restore
        client.restore()
        self.assertFalse(client.is_deleted)
        self.assertIsNone(client.deleted_at)
        self.assertIsNone(client.deleted_by)
        
        # Debe aparecer en queryset normal
        restored_client = Client.objects.get(id=client.id)
        self.assertEqual(restored_client.name, 'Test Client')
    
    def test_rls_isolation_con_soft_delete(self):
        """Verificar que RLS sigue funcionando con soft delete."""
        from apps.clients_api.models import Client
        
        # Simular contexto de tenant
        with connection.cursor() as cursor:
            cursor.execute("SELECT set_config('app.current_tenant_id', '1', true)")
        
        # Crear clientes en diferentes tenants
        client_t1 = Client.objects.create(name='Client T1', tenant_id=1)
        client_t2 = Client.objects.create(name='Client T2', tenant_id=2)
        
        # Soft delete cliente de tenant 1
        client_t1.soft_delete(user=self.user)
        
        # RLS debe seguir aislando por tenant
        # (Esto requiere que RLS esté configurado correctamente)
        visible_clients = Client.objects.all()
        
        # Solo debe ver clientes de su tenant (activos)
        for client in visible_clients:
            self.assertEqual(client.tenant_id, 1)


class AuditTrailTestCase(TestCase):
    """Tests para audit trail."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email='audit@test.com',
            password='testpass123',
            tenant_id=1
        )
    
    def test_auditoria_se_registra_correctamente(self):
        """Verificar que auditoría se registra."""
        from apps.clients_api.models import Client
        from apps.audit_api.audit_models import AuditService
        
        client = Client.objects.create(name='Test Client', tenant_id=1)
        
        # Registrar auditoría manualmente
        audit_log = AuditService.log_action(
            tenant_id=1,
            actor=self.user,
            action=AuditAction.CREATE,
            content_object=client,
            changes={'name': 'Test Client'}
        )
        
        # Verificar registro de auditoría
        self.assertEqual(audit_log.tenant_id, 1)
        self.assertEqual(audit_log.actor, self.user)
        self.assertEqual(audit_log.action, AuditAction.CREATE)
        self.assertEqual(audit_log.content_object, client)
        self.assertEqual(audit_log.changes['name'], 'Test Client')
    
    def test_auditoria_soft_delete(self):
        """Verificar auditoría de soft delete."""
        from apps.clients_api.models import Client
        from apps.audit_api.audit_models import AuditService
        
        client = Client.objects.create(name='Test Client', tenant_id=1)
        
        # Soft delete con auditoría
        AuditService.log_soft_delete(
            tenant_id=1,
            actor=self.user,
            instance=client
        )
        
        # Verificar registro de auditoría
        audit_logs = BusinessAuditLog.objects.filter(
            content_type__model='client',
            object_id=client.id,
            action=AuditAction.SOFT_DELETE
        )
        
        self.assertEqual(audit_logs.count(), 1)
        audit_log = audit_logs.first()
        self.assertEqual(audit_log.actor, self.user)
        self.assertEqual(audit_log.tenant_id, 1)
    
    def test_auditoria_aislada_por_tenant(self):
        """Verificar que auditoría respeta aislamiento por tenant."""
        from apps.clients_api.models import Client
        from apps.audit_api.audit_models import AuditService
        
        # Crear clientes en diferentes tenants
        client_t1 = Client.objects.create(name='Client T1', tenant_id=1)
        client_t2 = Client.objects.create(name='Client T2', tenant_id=2)
        
        # Auditoría para cada tenant
        AuditService.log_action(
            tenant_id=1, actor=self.user, action=AuditAction.CREATE,
            content_object=client_t1
        )
        AuditService.log_action(
            tenant_id=2, actor=self.user, action=AuditAction.CREATE,
            content_object=client_t2
        )
        
        # Verificar aislamiento
        audit_t1 = BusinessAuditLog.objects.filter(tenant_id=1)
        audit_t2 = BusinessAuditLog.objects.filter(tenant_id=2)
        
        self.assertEqual(audit_t1.count(), 1)
        self.assertEqual(audit_t2.count(), 1)
        self.assertEqual(audit_t1.first().content_object, client_t1)
        self.assertEqual(audit_t2.first().content_object, client_t2)