"""Sistema de eventos de dominio para tenant activation"""
from django.dispatch import Signal, receiver
from apps.roles_api.models import Role, UserRole

# Definir señal de dominio
tenant_activated = Signal()

@receiver(tenant_activated)
def create_owner_userrole(sender, tenant, owner, **kwargs):
    """Crear UserRole contextual cuando se activa un tenant"""
    try:
        client_admin_role = Role.objects.get(name='CLIENT_ADMIN')
        
        # Crear UserRole contextual si no existe
        user_role, created = UserRole.objects.get_or_create(
            user=owner,
            role=client_admin_role,
            tenant=tenant
        )
        
        if created:
            print(f"UserRole contextual creado: {owner.email} → CLIENT_ADMIN @ {tenant.name}")
        
    except Role.DoesNotExist:
        print(f"ERROR: Role CLIENT_ADMIN no existe para tenant {tenant.name}")