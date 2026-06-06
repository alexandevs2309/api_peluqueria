import json
import logging

from django.db.models.signals import post_save, pre_save
from django.db.models import Q
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
from .models import NotificationTemplate, InAppNotification
from .services import NotificationService
from .sse import publish_notification_event

@receiver(post_save, sender=InAppNotification)
def inapp_notification_created(sender, instance, created, **kwargs):
    """Publica en Redis PubSub cuando se crea una notificación in-app."""
    if created and instance.recipient_id:
        publish_notification_event(
            instance.recipient_id,
            {
                "type": "notification",
                "id": instance.id,
                "notification_type": instance.type,
                "title": instance.title,
                "message": instance.message,
                "is_read": instance.is_read,
                "created_at": instance.created_at.isoformat() if instance.created_at else None,
            },
        )


@receiver(post_save, sender='appointments_api.Appointment')
def appointment_created(sender, instance, created, **kwargs):
    """Enviar notificación cuando se crea una cita"""
    if created:
        from .models import InAppNotification
        stylist = instance.stylist
        client = instance.client
        client_name = client.full_name if client else 'Cliente'
        
        # Notificación in-app para el estilista
        if stylist:
            InAppNotification.objects.create(
                recipient=stylist,
                type='appointment',
                title='Nueva cita programada',
                message=f"Cita con {client_name} el {instance.date_time.strftime('%d/%m/%Y a las %H:%M')}"
            )
        
        # Notificación SMS al cliente
        if client and client.phone:
            phone = client.phone
            if not phone.startswith('+'):
                phone = f'+1{phone}' if phone.isdigit() else phone
            from .tasks import send_sms
            send_sms.delay(
                phone=phone,
                message=f"Recordatorio: Tienes una cita en la barbería el {instance.date_time.strftime('%d/%m/%Y')} a las {instance.date_time.strftime('%H:%M')}. Confirma o reagenda."
            )

        # Notificación por email (si existe template)
        service = NotificationService()
        try:
            tenant = getattr(stylist, 'tenant', None) if stylist else None
            template = NotificationTemplate.objects.get(
                Q(notification_type='appointment_confirmation'),
                Q(type='email'),
                Q(tenant=tenant) | Q(tenant__isnull=True),
                is_active=True
            )
            
            context = {
                'client_name': client_name,
                'appointment_date': instance.date_time.strftime('%d/%m/%Y'),
                'appointment_time': instance.date_time.strftime('%H:%M'),
                'stylist_name': stylist.full_name if stylist else 'Por asignar',
                'service_name': instance.service.name if instance.service else 'Por definir'
            }
            
            recipient_user = client.user if client and hasattr(client, 'user') else None
            if recipient_user:
                service.create_notification(
                    recipient=recipient_user,
                    template=template,
                    context_data=context
                )
        except NotificationTemplate.DoesNotExist:
            pass

@receiver(pre_save, sender='appointments_api.Appointment')
def appointment_status_changed(sender, instance, **kwargs):
    """Notificar cuando cambia el estado de una cita"""
    if not instance.pk:
        return
    try:
        from .models import InAppNotification
        old_instance = sender.objects.get(pk=instance.pk)
        stylist = instance.stylist
        client = instance.client
        client_name = client.full_name if client else 'Cliente'

        if not stylist:
            return

        # Detectar cambio de estado
        if old_instance.status != instance.status:
            status_messages = {
                'completed': f"Cita completada con {client_name}",
                'cancelled': f"Cita cancelada: {client_name} - {instance.date_time.strftime('%d/%m/%Y %H:%M')}",
                'no_show': f"Cliente no asistió: {client_name} - {instance.date_time.strftime('%d/%m/%Y %H:%M')}",
            }

            if instance.status in status_messages:
                InAppNotification.objects.create(
                    recipient=stylist,
                    type='appointment',
                    title=f'Cambio de estado: {instance.get_status_display()}',
                    message=status_messages[instance.status]
                )

        # Detectar reprogramación
        if old_instance.date_time != instance.date_time:
            InAppNotification.objects.create(
                recipient=stylist,
                type='appointment',
                title='Cita reprogramada',
                message=f"Cita con {client_name} movida de {old_instance.date_time.strftime('%d/%m/%Y %H:%M')} a {instance.date_time.strftime('%d/%m/%Y %H:%M')}"
            )
    except sender.DoesNotExist:
        pass

@receiver(post_save, sender='pos_api.Sale')
def sale_completed(sender, instance, created, **kwargs):
    """Notificar cuando se completa una venta"""
    if created and instance.employee:
        service = NotificationService()
        
        try:
            tenant = getattr(instance.employee.user, 'tenant', None) if instance.employee else None
            template = NotificationTemplate.objects.get(
                Q(notification_type='earnings_available'),
                Q(type='email'),
                Q(tenant=tenant) | Q(tenant__isnull=True),
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
            tenant = getattr(instance, 'tenant', None)
            template = NotificationTemplate.objects.get(
                Q(notification_type='stock_alert'),
                Q(type='email'),
                Q(tenant=tenant) | Q(tenant__isnull=True),
                is_active=True
            )
            
            # Notificar a administradores del tenant
            from apps.auth_api.models import User
            admins = User.objects.filter(
                tenant=instance.tenant,
                roles__name='Client-Admin'  # Solo Client-Admin, no Super-Admin
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
    end_date = getattr(instance, 'end_date', None)
    if end_date:
        days_until_expiry = (end_date - timezone.now().date()).days
        
        if days_until_expiry in [7, 3, 1]:  # Notificar 7, 3 y 1 día antes
            service = NotificationService()
            
            try:
                tenant = getattr(instance, 'tenant', None)
                template = NotificationTemplate.objects.get(
                    Q(notification_type='subscription_expiring'),
                    Q(type='email'),
                    Q(tenant=tenant) | Q(tenant__isnull=True),
                    is_active=True
                )
                
                context = {
                    'tenant_name': instance.tenant.name,
                    'plan_name': instance.plan.name,
                    'expiry_date': end_date.strftime('%d/%m/%Y'),
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


