from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from apps.auth_api.models import User
from .models import Employee
import logging

logger = logging.getLogger(__name__)

# Roles que requieren registro Employee automático
EMPLOYEE_ROLES = ['Estilista', 'Cajera', 'Manager', 'Utility']

@receiver(post_save, sender=User)
def create_employee_for_staff_user(sender, instance, created, **kwargs):
    """
    Crear Employee automáticamente cuando se crea un User con rol de empleado.
    Garantiza integridad de dominio User-Employee en SaaS multi-tenant.
    """
    # Solo procesar si es creación de usuario (no actualización)
    if not created:
        return
    
    # Solo para usuarios con roles de empleado
    if not instance.role or instance.role not in EMPLOYEE_ROLES:
        return
    
    # Usuario debe tener tenant asignado
    if not instance.tenant:
        logger.warning(f"User {instance.id} ({instance.email}) tiene rol empleado pero sin tenant")
        return
    
    try:
        with transaction.atomic():
            # Crear Employee solo si no existe (idempotente)
            employee, created_emp = Employee.objects.get_or_create(
                user=instance,
                defaults={
                    'tenant': instance.tenant,
                    'is_active': True,
                    'specialty': '',
                    'phone': '',
                }
            )
            
            if created_emp:
                logger.info(f"Employee creado automáticamente para User {instance.id} ({instance.email}) en tenant {instance.tenant}")
            else:
                logger.info(f"Employee ya existe para User {instance.id} ({instance.email})")
                
    except Exception as e:
        logger.error(f"Error creando Employee para User {instance.id}: {str(e)}")
        # No re-raise para evitar fallar la creación del User
        # El Employee se puede crear manualmente después si es necesario