from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import NotificationTemplate
from .services import NotificationService

@receiver(post_save, sender='appointments_api.Appointment')
def appointment_created(sender, instance, created, **kwargs):
    """Enviar notificación cuando se crea una cita"""
    if created:
        service = NotificationService()
        
        # Notificación de confirmación al cliente
        try:
            template = NotificationTemplate.objects.get(
                notification_type='appointment_confirmation',
                type='email',
                is_active=True
            )
            
            context = {
                'client_name': instance.client.full_name,
                'appointment_date': instance.date_time.strftime('%d/%m/%Y'),
                'appointment_time': instance.date_time.strftime('%H:%M'),
                'stylist_name': instance.stylist.full_name if instance.stylist else 'Por asignar',
                'service_name': instance.service.name if instance.service else 'Por definir'
            }
            
            service.create_notification(
                recipient=instance.client.user if hasattr(instance.client, 'user') else None,
                template=template,
                context_data=context
            )
        except NotificationTemplate.DoesNotExist:
            pass

@receiver(post_save, sender='pos_api.Sale')
def sale_completed(sender, instance, created, **kwargs):
    """Notificar cuando se completa una venta"""
    if created and instance.employee:
        service = NotificationService()
        
        try:
            template = NotificationTemplate.objects.get(
                notification_type='earnings_available',
                type='email',
                is_active=True
            )
            
            context = {
                'employee_name': instance.employee.user.full_name,
                'sale_amount': f"${instance.total:,.2f}",
                'sale_date': instance.date_time.strftime('%d/%m/%Y %H:%M'),
                'commission_rate': instance.employee.commission_rate or 40
            }
            
            service.create_notification(
                recipient=instance.employee.user,
                template=template,
                context_data=context
            )
        except NotificationTemplate.DoesNotExist:
            pass

@receiver(post_save, sender='inventory_api.Product')
def product_low_stock(sender, instance, **kwargs):
    """Notificar cuando un producto tiene stock bajo"""
    if instance.stock <= instance.min_stock and instance.is_active:
        service = NotificationService()
        
        try:
            template = NotificationTemplate.objects.get(
                notification_type='stock_alert',
                type='email',
                is_active=True
            )
            
            # Notificar a administradores del tenant
            from apps.auth_api.models import User
            admins = User.objects.filter(
                tenant=instance.tenant,
                roles__name__in=['Client-Admin', 'Super-Admin']
            )
            
            context = {
                'product_name': instance.name,
                'current_stock': instance.stock,
                'min_stock': instance.min_stock,
                'supplier': instance.supplier.name if instance.supplier else 'Sin proveedor'
            }
            
            for admin in admins:
                service.create_notification(
                    recipient=admin,
                    template=template,
                    context_data=context,
                    priority='high'
                )
        except NotificationTemplate.DoesNotExist:
            pass

@receiver(post_save, sender='subscriptions_api.Subscription')
def subscription_expiring(sender, instance, **kwargs):
    """Notificar cuando una suscripción está por vencer"""
    if instance.end_date:
        days_until_expiry = (instance.end_date - timezone.now().date()).days
        
        if days_until_expiry in [7, 3, 1]:  # Notificar 7, 3 y 1 día antes
            service = NotificationService()
            
            try:
                template = NotificationTemplate.objects.get(
                    notification_type='subscription_expiring',
                    type='email',
                    is_active=True
                )
                
                context = {
                    'tenant_name': instance.tenant.name,
                    'plan_name': instance.plan.name,
                    'expiry_date': instance.end_date.strftime('%d/%m/%Y'),
                    'days_remaining': days_until_expiry
                }
                
                # Notificar a administradores del tenant
                from apps.auth_api.models import User
                admins = User.objects.filter(
                    tenant=instance.tenant,
                    roles__name='Client-Admin'
                )
                
                for admin in admins:
                    service.create_notification(
                        recipient=admin,
                        template=template,
                        context_data=context,
                        priority='urgent' if days_until_expiry <= 1 else 'high'
                    )
            except NotificationTemplate.DoesNotExist:
                pass

# Función para crear recordatorios de citas
def create_appointment_reminders():
    """Función para ejecutar con Celery - crear recordatorios de citas"""
    from apps.appointments_api.models import Appointment
    
    # Citas para mañana
    tomorrow = timezone.now().date() + timedelta(days=1)
    appointments = Appointment.objects.filter(
        date_time__date=tomorrow,
        status='scheduled'
    ).select_related('client', 'stylist', 'service')
    
    service = NotificationService()
    
    try:
        template = NotificationTemplate.objects.get(
            notification_type='appointment_reminder',
            type='email',
            is_active=True
        )
        
        for appointment in appointments:
            context = {
                'client_name': appointment.client.full_name,
                'appointment_date': appointment.date_time.strftime('%d/%m/%Y'),
                'appointment_time': appointment.date_time.strftime('%H:%M'),
                'stylist_name': appointment.stylist.full_name if appointment.stylist else 'Por asignar',
                'service_name': appointment.service.name if appointment.service else 'Por definir'
            }
            
            service.create_notification(
                recipient=appointment.client.user if hasattr(appointment.client, 'user') else None,
                template=template,
                context_data=context,
                scheduled_at=timezone.now() + timedelta(hours=1)  # Enviar en 1 hora
            )
    except NotificationTemplate.DoesNotExist:
        pass