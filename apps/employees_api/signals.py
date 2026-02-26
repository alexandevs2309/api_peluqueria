from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.auth_api.models import User
from .models import Employee


@receiver(post_save, sender=User)
def create_employee_for_staff(sender, instance, created, **kwargs):
    """
    Crear automáticamente un Employee cuando se crea un User con rol de empleado
    """
    if created and instance.tenant_id:
        employee_roles = ['Cajera', 'Estilista', 'Manager', 'Client-Staff', 'Utility']
        
        if instance.role in employee_roles:
            # Validación defensiva: tenant debe existir
            if not instance.tenant_id:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Cannot create Employee for User {instance.id}: tenant_id is None")
                return
            
            # Verificar que no exista ya un Employee para este usuario
            if not Employee.objects.filter(user=instance).exists():
                Employee.objects.create(
                    user=instance,
                    tenant_id=instance.tenant_id,
                    is_active=instance.is_active
                )
