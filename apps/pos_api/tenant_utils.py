"""
Utilidades para aislamiento de tenant en POS
FASE 1: Solo seguridad crítica
"""
from django.db.models import Q

def get_tenant_sales_filter(user):
    """
    Filtro seguro para ventas por tenant
    Evita bypass de seguridad en queries complejas
    """
    if not user.tenant:
        return Q(pk__isnull=True)  # Sin acceso si no tiene tenant
    
    # Ventas del tenant: empleado del tenant O usuario del tenant sin empleado
    return Q(
        Q(employee__tenant=user.tenant) | 
        Q(user__tenant=user.tenant, employee__isnull=True)
    )

def validate_tenant_ownership(user, employee=None, client=None, product=None):
    """
    Validar que recursos pertenecen al tenant del usuario
    """
    if not user.tenant:
        raise ValueError("Usuario sin tenant asignado")
    
    if employee and employee.tenant != user.tenant:
        raise ValueError("Empleado no pertenece al tenant")
    
    if client and client.tenant != user.tenant:
        raise ValueError("Cliente no pertenece al tenant")
    
    if product and hasattr(product, 'tenant') and product.tenant != user.tenant:
        raise ValueError("Producto no pertenece al tenant")
    
    return True