"""
EJEMPLO DE MIGRACIÓN A TenantScopedViewSet

Este archivo muestra cómo migrar ViewSets existentes a la clase base.
NO reemplaza views.py existentes, solo documenta el patrón recomendado.
"""

from rest_framework import permissions
from apps.tenants_api.base_viewsets import TenantScopedViewSet, TenantScopedReadOnlyViewSet
from apps.services_api.models import Service
from apps.services_api.serializers import ServiceSerializer


# ============================================================================
# PATRÓN ANTIGUO (código duplicado)
# ============================================================================

class ServiceViewSet_OLD(viewsets.ModelViewSet):
    """
    ⚠️ PATRÓN ANTIGUO: Código duplicado en get_queryset()
    """
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # ⚠️ Este código se repite en TODOS los ViewSets
        user = self.request.user
        
        if user.is_superuser:
            return Service.objects.all()
        
        if not user.tenant:
            return Service.objects.none()
        
        return Service.objects.filter(tenant=user.tenant)

    def perform_create(self, serializer):
        # ⚠️ Este código también se repite
        user = self.request.user
        
        if user.is_superuser:
            tenant = user.tenant or Tenant.objects.first()
        else:
            if not user.tenant:
                raise ValidationError("Usuario sin tenant asignado")
            tenant = user.tenant
        
        serializer.save(tenant=tenant)


# ============================================================================
# PATRÓN NUEVO (usando clase base)
# ============================================================================

class ServiceViewSet(TenantScopedViewSet):
    """
    ✅ PATRÓN NUEVO: Hereda filtrado automático por tenant
    
    VENTAJAS:
    - Sin código duplicado
    - Comportamiento consistente
    - Más fácil de mantener
    - Menos propenso a errores
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # ✅ get_queryset() y perform_create() ya están implementados
    # ✅ No necesitas escribir código de filtrado


# ============================================================================
# PATRÓN CON LÓGICA ADICIONAL
# ============================================================================

class ServiceViewSet_WithCustomLogic(TenantScopedViewSet):
    """
    ✅ PATRÓN: Agregar lógica adicional sobre la base
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # ✅ Llamar a super() para obtener filtrado por tenant
        qs = super().get_queryset()
        
        # ✅ Agregar lógica adicional
        # Ejemplo: Filtrar solo servicios activos
        qs = qs.filter(is_active=True)
        
        # Ejemplo: Ordenar por nombre
        qs = qs.order_by('name')
        
        return qs
    
    def perform_create(self, serializer):
        # ✅ Llamar a super() para asignar tenant
        super().perform_create(serializer)
        
        # ✅ Lógica adicional después de crear
        # Ejemplo: Enviar notificación
        # send_notification(serializer.instance)


# ============================================================================
# PATRÓN READ-ONLY
# ============================================================================

class ServiceReadOnlyViewSet(TenantScopedReadOnlyViewSet):
    """
    ✅ PATRÓN: ViewSet de solo lectura con filtrado por tenant
    """
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.IsAuthenticated]


# ============================================================================
# MIGRACIÓN PASO A PASO
# ============================================================================

"""
CÓMO MIGRAR UN VIEWSET EXISTENTE:

1. IDENTIFICAR ViewSet con patrón de filtrado por tenant

2. CAMBIAR herencia:
   ANTES: class MyViewSet(viewsets.ModelViewSet):
   DESPUÉS: class MyViewSet(TenantScopedViewSet):

3. AGREGAR import:
   from apps.tenants_api.base_viewsets import TenantScopedViewSet

4. ELIMINAR get_queryset() si solo filtra por tenant:
   ANTES:
       def get_queryset(self):
           if user.is_superuser:
               return Model.objects.all()
           return Model.objects.filter(tenant=user.tenant)
   
   DESPUÉS:
       # ✅ Eliminar método completo, ya está en la clase base

5. ELIMINAR perform_create() si solo asigna tenant:
   ANTES:
       def perform_create(self, serializer):
           serializer.save(tenant=self.request.user.tenant)
   
   DESPUÉS:
       # ✅ Eliminar método completo, ya está en la clase base

6. MANTENER lógica adicional si existe:
   def get_queryset(self):
       qs = super().get_queryset()  # ✅ Obtener filtrado por tenant
       qs = qs.filter(is_active=True)  # ✅ Lógica adicional
       return qs

7. PROBAR:
   - SuperAdmin ve todos los registros
   - Usuario con tenant ve solo sus registros
   - Usuario sin tenant no ve nada
   - Crear registros asigna tenant correctamente

NO MIGRAR TODOS LOS VIEWSETS DE GOLPE.
Migrar progresivamente según prioridad.

VIEWSETS CANDIDATOS PARA MIGRACIÓN:
- ServiceViewSet ✅
- ClientViewSet ✅
- AppointmentViewSet ✅
- ProductViewSet ✅
- ReportViewSet ✅

VIEWSETS QUE NO DEBEN MIGRAR:
- TenantViewSet (gestiona tenants, no pertenece a tenant)
- UserViewSet (lógica compleja de roles)
- ViewSets con lógica de negocio compleja
"""
