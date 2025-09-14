from rest_framework.exceptions import ValidationError
from .utils import get_user_active_subscription

class SubscriptionLimitValidator:
    """Validador para límites de suscripción"""
    
    @staticmethod
    def validate_employee_limit(user, tenant=None):
        """Valida límite de empleados según el plan"""
        from apps.employees_api.models import Employee
        
        # Super-Admin sin límites
        if user.roles.filter(name='Super-Admin').exists():
            return True
            
        # Obtener suscripción activa
        subscription = get_user_active_subscription(user)
        if not subscription:
            # Sin suscripción = plan gratuito (1 empleado)
            max_employees = 1
        else:
            max_employees = subscription.plan.max_employees
            
        # 0 = ilimitado
        if max_employees == 0:
            return True
            
        # Contar empleados actuales
        current_tenant = tenant or getattr(user, 'tenant', None)
        if not current_tenant:
            return True
            
        current_count = Employee.objects.filter(tenant=current_tenant).count()
        
        if current_count >= max_employees:
            raise ValidationError(
                f"Has alcanzado el límite de empleados de tu plan ({max_employees}). "
                f"Actualiza tu suscripción para agregar más empleados."
            )
            
        return True
    
    @staticmethod
    def validate_client_limit(user, tenant=None):
        """Valida límite de clientes según el plan"""
        from apps.clients_api.models import Client
        
        # Super-Admin sin límites
        if user.roles.filter(name='Super-Admin').exists():
            return True
            
        subscription = get_user_active_subscription(user)
        if not subscription:
            max_clients = 50  # Plan gratuito
        else:
            max_clients = getattr(subscription.plan, 'max_clients', 0)
            
        if max_clients == 0:
            return True
            
        current_tenant = tenant or getattr(user, 'tenant', None)
        if not current_tenant:
            return True
            
        current_count = Client.objects.filter(tenant=current_tenant).count()
        
        if current_count >= max_clients:
            raise ValidationError(
                f"Has alcanzado el límite de clientes de tu plan ({max_clients}). "
                f"Actualiza tu suscripción para agregar más clientes."
            )
            
        return True
    
    @staticmethod
    def validate_appointment_limit(user, tenant=None):
        """Valida límite de citas por mes según el plan"""
        from apps.appointments_api.models import Appointment
        from django.utils import timezone
        from datetime import datetime
        
        # Super-Admin sin límites
        if user.roles.filter(name='Super-Admin').exists():
            return True
            
        subscription = get_user_active_subscription(user)
        if not subscription:
            max_appointments = 100  # Plan gratuito
        else:
            max_appointments = getattr(subscription.plan, 'max_appointments_per_month', 0)
            
        if max_appointments == 0:
            return True
            
        current_tenant = tenant or getattr(user, 'tenant', None)
        if not current_tenant:
            return True
            
        # Contar citas del mes actual
        now = timezone.now()
        start_month = datetime(now.year, now.month, 1)
        
        current_count = Appointment.objects.filter(
            stylist__tenant=current_tenant,
            date_time__gte=start_month,
            date_time__month=now.month
        ).count()
        
        if current_count >= max_appointments:
            raise ValidationError(
                f"Has alcanzado el límite de citas mensuales de tu plan ({max_appointments}). "
                f"Actualiza tu suscripción para programar más citas."
            )
            
        return True