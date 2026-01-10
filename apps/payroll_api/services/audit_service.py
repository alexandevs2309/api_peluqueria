"""
Servicios de dominio con auditoría integrada
apps/payroll_api/services/audit_service.py
"""
from typing import Optional, Dict, Any
from django.db import transaction
from apps.audit_api.audit_models import AuditService, AuditAction


class PayrollAuditService:
    """Servicio de payroll con auditoría automática."""
    
    @staticmethod
    @transaction.atomic
    def create_payroll_calculation(
        tenant_id: int,
        actor,
        calculation_data: Dict[str, Any],
        request=None
    ):
        """Crear cálculo de nómina con auditoría."""
        from apps.payroll_api.models import PayrollCalculation
        
        calculation = PayrollCalculation.objects.create(**calculation_data)
        
        # Auditoría automática
        AuditService.log_action(
            tenant_id=tenant_id,
            actor=actor,
            action=AuditAction.CREATE,
            content_object=calculation,
            changes=calculation_data,
            request=request
        )
        
        return calculation
    
    @staticmethod
    @transaction.atomic
    def soft_delete_calculation(
        calculation_id: int,
        tenant_id: int,
        actor,
        request=None
    ):
        """Soft delete con auditoría."""
        from apps.payroll_api.models import PayrollCalculation
        
        calculation = PayrollCalculation.objects.get(
            id=calculation_id,
            tenant_id=tenant_id
        )
        
        # Capturar estado previo
        previous_state = {
            'is_deleted': calculation.is_deleted,
            'deleted_at': calculation.deleted_at,
        }
        
        # Soft delete
        calculation.soft_delete(user=actor)
        
        # Auditoría
        AuditService.log_action(
            tenant_id=tenant_id,
            actor=actor,
            action=AuditAction.SOFT_DELETE,
            content_object=calculation,
            previous_values=previous_state,
            request=request
        )
        
        return calculation


class ClientAuditService:
    """Servicio de clientes con auditoría."""
    
    @staticmethod
    @transaction.atomic
    def update_client(
        client_id: int,
        tenant_id: int,
        actor,
        update_data: Dict[str, Any],
        request=None
    ):
        """Actualizar cliente con auditoría de cambios."""
        from apps.clients_api.models import Client
        
        client = Client.objects.get(id=client_id, tenant_id=tenant_id)
        
        # Capturar valores previos
        previous_values = {}
        changes = {}
        
        for field, new_value in update_data.items():
            if hasattr(client, field):
                old_value = getattr(client, field)
                if old_value != new_value:
                    previous_values[field] = old_value
                    changes[field] = new_value
                    setattr(client, field, new_value)
        
        if changes:
            client.save(update_fields=list(changes.keys()))
            
            # Auditoría solo si hay cambios reales
            AuditService.log_action(
                tenant_id=tenant_id,
                actor=actor,
                action=AuditAction.UPDATE,
                content_object=client,
                changes=changes,
                previous_values=previous_values,
                request=request
            )
        
        return client