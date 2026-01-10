"""
Mixins para ViewSets con soft delete compatible
apps/utils/mixins.py
"""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from apps.audit_api.audit_models import AuditService, AuditAction


class SoftDeleteMixin:
    """
    Mixin para ViewSets que maneja soft delete.
    Mantiene compatibilidad con frontend existente.
    """
    
    def destroy(self, request, *args, **kwargs):
        """
        Override destroy para usar soft delete.
        Mantiene mismo contrato HTTP (DELETE -> 204).
        """
        instance = self.get_object()
        
        # Soft delete en lugar de hard delete
        with transaction.atomic():
            instance.soft_delete(user=request.user)
            
            # Auditoría automática
            AuditService.log_action(
                tenant_id=getattr(instance, 'tenant_id', None),
                actor=request.user,
                action=AuditAction.SOFT_DELETE,
                content_object=instance,
                request=request
            )
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """
        Endpoint adicional para restaurar registros soft-deleted.
        POST /api/resource/{id}/restore/
        """
        # Buscar en registros eliminados
        queryset = self.get_queryset().model.all_objects.filter(
            pk=pk,
            is_deleted=True
        )
        
        if hasattr(self.get_queryset().model, 'tenant_id'):
            tenant_id = getattr(request.user, 'tenant_id', None)
            queryset = queryset.filter(tenant_id=tenant_id)
        
        try:
            instance = queryset.get()
        except self.get_queryset().model.DoesNotExist:
            return Response(
                {'error': 'Registro no encontrado o no eliminado'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        with transaction.atomic():
            instance.restore()
            
            # Auditoría
            AuditService.log_action(
                tenant_id=getattr(instance, 'tenant_id', None),
                actor=request.user,
                action=AuditAction.RESTORE,
                content_object=instance,
                request=request
            )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def deleted(self, request):
        """
        Lista registros soft-deleted.
        GET /api/resource/deleted/
        """
        queryset = self.get_queryset().model.all_objects.filter(
            is_deleted=True
        )
        
        # Filtrar por tenant si aplica
        if hasattr(self.get_queryset().model, 'tenant_id'):
            tenant_id = getattr(request.user, 'tenant_id', None)
            queryset = queryset.filter(tenant_id=tenant_id)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AuditableMixin:
    """
    Mixin para capturar cambios en create/update.
    """
    
    def perform_create(self, serializer):
        """Override create con auditoría."""
        instance = serializer.save()
        
        # Auditoría de creación
        AuditService.log_action(
            tenant_id=getattr(instance, 'tenant_id', None),
            actor=self.request.user,
            action=AuditAction.CREATE,
            content_object=instance,
            changes=serializer.validated_data,
            request=self.request
        )
    
    def perform_update(self, serializer):
        """Override update con auditoría de cambios."""
        instance = serializer.instance
        
        # Capturar valores previos
        previous_values = {}
        for field in serializer.validated_data.keys():
            if hasattr(instance, field):
                previous_values[field] = getattr(instance, field)
        
        # Actualizar
        updated_instance = serializer.save()
        
        # Auditoría solo si hay cambios
        if serializer.validated_data:
            AuditService.log_action(
                tenant_id=getattr(updated_instance, 'tenant_id', None),
                actor=self.request.user,
                action=AuditAction.UPDATE,
                content_object=updated_instance,
                changes=serializer.validated_data,
                previous_values=previous_values,
                request=self.request
            )