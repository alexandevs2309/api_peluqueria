import json
import logging
from apps.emails.service import EmailRenderer

logger = logging.getLogger(__name__)

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
        from django.db import transaction
        transaction.on_commit(lambda: publish_notification_event(
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
        ))


@receiver(post_save, sender='appointments_api.Appointment')
def appointment_created(sender, instance, created, **kwargs):
    """Enviar notificación cuando se crea una cita"""
    if not created:
        return

    from django.db import transaction

    def send_appointment_notifications():
        from .models import InAppNotification
        stylist = instance.stylist
        client = instance.client
        client_name = client.full_name if client else 'Cliente'
        service_name = instance.service.name if getattr(instance, 'service', None) else 'Servicio'
        dt_label = instance.date_time.strftime('%d/%m/%Y a las %H:%M') if instance.date_time else ''

        # Notificación in-app para el estilista
        if stylist:
            InAppNotification.objects.create(
                recipient=stylist,
                type='appointment',
                title='Nueva cita programada',
                message=f"Cita con {client_name} el {dt_label}"
            )

        # Notificación in-app para el cliente (si tiene usuario vinculado)
        client_user = client.user if client and hasattr(client, 'user') and getattr(client, 'user', None) else None
        if client_user:
            InAppNotification.objects.get_or_create(
                recipient=client_user,
                type='appointment',
                title='Cita agendada',
                message=f"Tu cita de {service_name} fue agendada para el {dt_label}.",
                is_read=False,
                defaults={}
            )

        # Notificación in-app para administradores del tenant
        try:
            tenant = getattr(instance, 'tenant', None)
            if tenant:
                from apps.auth_api.models import User
                admin_ids = set(User.objects.filter(
                    tenant=tenant,
                    roles__name='Client-Admin',
                    is_active=True
                ).values_list('id', flat=True))
                for uid in admin_ids:
                    if stylist and uid == getattr(stylist, 'id', None):
                        continue
                    if client_user and uid == getattr(client_user, 'id', None):
                        continue
                    InAppNotification.objects.create(
                        recipient_id=uid,
                        type='appointment',
                        title='Nueva cita en la agenda',
                        message=f"{client_name} · {service_name} · {dt_label}"
                    )
        except Exception as e:
            logger.warning("Failed to create admin in-app notifications for appointment %s: %s", instance.id, str(e))

        # Notificación SMS al cliente
        if client and client.phone:
            phone = client.phone
            if not phone.startswith('+'):
                phone = f'+1{phone}' if phone.isdigit() else phone
            from .tasks import send_sms
            try:
                send_sms.delay(
                    phone=phone,
                    message=f"Recordatorio: Tienes una cita en la barbería el {instance.date_time.strftime('%d/%m/%Y')} a las {instance.date_time.strftime('%H:%M')}. Confirma o reagenda."
                )
            except Exception as e:
                logger.warning("Failed to send SMS to %s: %s", phone, str(e))

        # Notificación por email (si existe template)
        service = NotificationService()
        tenant = getattr(instance, 'tenant', None)
        email_context = {
            'client_name': client_name,
            'appointment_date': instance.date_time.strftime('%d/%m/%Y') if instance.date_time else '',
            'appointment_time': instance.date_time.strftime('%H:%M') if instance.date_time else '',
            'stylist_name': stylist.full_name if stylist else 'Por asignar',
            'service_name': service_name,
            'appointment_id': instance.id,
        }

        recipient_user = client_user
        if recipient_user:
            try:
                template = NotificationTemplate.objects.get(
                    Q(notification_type='appointment_confirmation'),
                    Q(type='email'),
                    Q(tenant=tenant) | Q(tenant__isnull=True),
                    is_active=True
                )
                service.create_notification(
                    recipient=recipient_user,
                    template=template,
                    context_data=email_context
                )
            except NotificationTemplate.DoesNotExist:
                pass
        elif client and client.email:
            from apps.settings_api.integration_service import IntegrationService
            attachments = []
            try:
                ics_content = service.generate_ics_content(
                    instance,
                    stylist_name=email_context['stylist_name'],
                    service_name=email_context['service_name'],
                    client_name=email_context['client_name']
                )
                attachments.append(('invitacion.ics', ics_content, 'text/calendar'))
            except Exception as e:
                logger.warning("Failed to generate standalone ICS: %s", str(e))

            try:
                template = NotificationTemplate.objects.get(
                    Q(notification_type='appointment_confirmation'),
                    Q(type='email'),
                    Q(tenant=tenant) | Q(tenant__isnull=True),
                    is_active=True
                )
                message = service._render_template(template.body, email_context)
                subject = service._render_template(template.subject or 'Confirmación de cita', email_context)
                try:
                    IntegrationService.send_email(
                        to_email=client.email,
                        subject=subject,
                        message=message,
                        attachments=attachments,
                    )
                except Exception as e:
                    logger.warning("Failed to send confirmation email to %s: %s", client.email, str(e))
            except NotificationTemplate.DoesNotExist:
                try:
                    fallback_html = EmailRenderer.render('trial_content.html', {
                        'title': 'Confirmación de cita',
                        'content': f"Hola {client_name}, tu cita fue agendada para el {email_context['appointment_date']} a las {email_context['appointment_time']} con {email_context['stylist_name']}.",
                    })
                    IntegrationService.send_email(
                        to_email=client.email,
                        subject="Confirmación de cita",
                        message=fallback_html,
                        attachments=attachments,
                    )
                except Exception as e:
                    logger.warning("Failed to send fallback confirmation email to %s: %s", client.email, str(e))

        # WhatsApp al cliente (si existe template y tiene teléfono)
        if client and client.phone:
            wa_context = {
                'client_name': client_name,
                'appointment_date': instance.date_time.strftime('%d/%m/%Y') if instance.date_time else '',
                'appointment_time': instance.date_time.strftime('%H:%M') if instance.date_time else '',
                'stylist_name': stylist.full_name if stylist else 'Por asignar',
                'service_name': service_name
            }
            try:
                wa_template = NotificationTemplate.objects.get(
                    Q(notification_type='appointment_confirmation'),
                    Q(type='whatsapp'),
                    Q(tenant=tenant) | Q(tenant__isnull=True),
                    is_active=True
                )
                if client_user:
                    service.create_notification(
                        recipient=client_user,
                        template=wa_template,
                        context_data=wa_context
                    )
                else:
                    from apps.settings_api.integration_service import IntegrationService
                    message = service._render_template(wa_template.body, wa_context)
                    try:
                        IntegrationService.send_whatsapp(
                            phone=client.phone,
                            message=message,
                            tenant=tenant,
                        )
                    except Exception as e:
                        logger.warning("Failed to send WhatsApp to %s: %s", client.phone, str(e))
            except NotificationTemplate.DoesNotExist:
                pass

    transaction.on_commit(send_appointment_notifications)

@receiver(pre_save, sender='appointments_api.Appointment')
def appointment_status_changed(sender, instance, **kwargs):
    """Notificar cuando cambia el estado de una cita"""
    if not instance.pk:
        return
    try:
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return

    from django.db import transaction
    from .models import InAppNotification

    stylist = instance.stylist
    client = instance.client
    client_name = client.full_name if client else 'Cliente'
    client_user = client.user if client and hasattr(client, 'user') and getattr(client, 'user', None) else None
    dt_label = instance.date_time.strftime('%d/%m/%Y %H:%M') if instance.date_time else ''
    service_name = instance.service.name if getattr(instance, 'service', None) else 'Servicio'

    notifications = []

    if old_instance.status != instance.status:
        status_titles = {
            'completed': 'Cita completada',
            'cancelled': 'Cita cancelada',
            'no_show': 'Cliente no asistió',
            'scheduled': 'Cita programada',
        }
        status_messages_stylist = {
            'completed': f"Cita completada con {client_name}",
            'cancelled': f"Cita cancelada: {client_name} - {dt_label}",
            'no_show': f"Cliente no asistió: {client_name} - {dt_label}",
            'scheduled': f"Cita programada: {client_name} - {dt_label}",
        }
        status_messages_client = {
            'completed': f"Tu cita de {service_name} fue marcada como completada ({dt_label}).",
            'cancelled': f"Tu cita de {service_name} del {dt_label} fue cancelada.",
            'no_show': f"Tu cita de {service_name} del {dt_label} fue marcada como no asistida.",
            'scheduled': f"Tu cita de {service_name} quedó programada para el {dt_label}.",
        }
        if instance.status in status_titles:
            title = status_titles[instance.status]
            if stylist:
                notifications.append((stylist.id, 'appointment', title, status_messages_stylist.get(instance.status, f"{client_name} - {dt_label}")))
            if client_user:
                notifications.append((client_user.id, 'appointment', title, status_messages_client.get(instance.status, f"Actualización de tu cita: {dt_label}")))

    if old_instance.date_time != instance.date_time:
        old_label = old_instance.date_time.strftime('%d/%m/%Y %H:%M') if old_instance.date_time else ''
        if stylist:
            notifications.append((stylist.id, 'appointment', 'Cita reprogramada', f"Cita con {client_name} movida de {old_label} a {dt_label}"))
        if client_user:
            notifications.append((client_user.id, 'appointment', 'Cita reprogramada', f"Tu cita de {service_name} fue movida de {old_label} a {dt_label}"))

    if not notifications:
        return

    seen = set()
    deduped = []
    for item in notifications:
        key = (item[0], item[2], item[3])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    def create_notifications():
        for recipient_id, ntype, title, message in deduped:
            try:
                InAppNotification.objects.create(
                    recipient_id=recipient_id,
                    type=ntype,
                    title=title,
                    message=message
                )
            except Exception as e:
                logger.warning("Failed to create appointment notification for user %s: %s", recipient_id, str(e))

    transaction.on_commit(create_notifications)

@receiver(post_save, sender='pos_api.Sale')
def sale_completed(sender, instance, created, **kwargs):
    """Notificar cuando se completa una venta"""
    if created and instance.employee:
        from django.db import transaction
        
        def send_sale_notifications():
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
                    'commission_rate': float(instance.employee.commission_rate or 40)
                }

                service.create_notification(
                    recipient=instance.employee.user,
                    template=template,
                    context_data=context
                )
            except NotificationTemplate.DoesNotExist:
                pass

            # WhatsApp al empleado
            try:
                tenant = getattr(instance.employee.user, 'tenant', None) if instance.employee else None
                wa_template = NotificationTemplate.objects.get(
                    Q(notification_type='earnings_available'),
                    Q(type='whatsapp'),
                    Q(tenant=tenant) | Q(tenant__isnull=True),
                    is_active=True
                )
                wa_context = {
                    'employee_name': instance.employee.user.full_name,
                    'sale_amount': f"${instance.total:,.2f}",
                    'sale_date': instance.date_time.strftime('%d/%m/%Y %H:%M'),
                    'commission_rate': float(instance.employee.commission_rate or 40)
                }
                if hasattr(instance.employee.user, 'phone') and instance.employee.user.phone:
                    service.create_notification(
                        recipient=instance.employee.user,
                        template=wa_template,
                        context_data=wa_context
                    )
            except NotificationTemplate.DoesNotExist:
                pass
                
        transaction.on_commit(send_sale_notifications)

@receiver(post_save, sender='inventory_api.Product')
def product_low_stock(sender, instance, **kwargs):
    """Notificar cuando un producto tiene stock bajo"""
    if instance.stock <= instance.min_stock and instance.is_active:
        from django.db import transaction
        
        def send_stock_notifications():
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

            # WhatsApp a administradores
            try:
                wa_template = NotificationTemplate.objects.get(
                    Q(notification_type='stock_alert'),
                    Q(type='whatsapp'),
                    Q(tenant=instance.tenant) | Q(tenant__isnull=True),
                    is_active=True
                )
                wa_context = {
                    'product_name': instance.name,
                    'current_stock': instance.stock,
                    'min_stock': instance.min_stock,
                    'supplier': instance.supplier.name if instance.supplier else 'Sin proveedor'
                }
                for admin in admins:
                    if hasattr(admin, 'phone') and admin.phone:
                        service.create_notification(
                            recipient=admin,
                            template=wa_template,
                            context_data=wa_context,
                            priority='high'
                        )
            except NotificationTemplate.DoesNotExist:
                pass
                
        transaction.on_commit(send_stock_notifications)


@receiver(post_save, sender='subscriptions_api.Subscription')
def subscription_expiring(sender, instance, **kwargs):
    """Notificar cuando una suscripción está por vencer"""
    end_date = getattr(instance, 'end_date', None)
    if end_date:
        days_until_expiry = (end_date - timezone.now().date()).days
        
        if days_until_expiry in [7, 3, 1]:  # Notificar 7, 3 y 1 día antes
            from django.db import transaction
            
            def send_subscription_notifications():
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

            # WhatsApp a administradores
            if end_date and days_until_expiry in [7, 3, 1]:
                try:
                    tenant = getattr(instance, 'tenant', None)
                    wa_template = NotificationTemplate.objects.get(
                        Q(notification_type='subscription_expiring'),
                        Q(type='whatsapp'),
                        Q(tenant=tenant) | Q(tenant__isnull=True),
                        is_active=True
                    )
                    wa_context = {
                        'tenant_name': instance.tenant.name,
                        'plan_name': instance.plan.name,
                        'expiry_date': end_date.strftime('%d/%m/%Y'),
                        'days_remaining': days_until_expiry
                    }
                    from apps.auth_api.models import User
                    admins = User.objects.filter(
                        tenant=instance.tenant,
                        roles__name='Client-Admin'
                    )
                    for admin in admins:
                        if hasattr(admin, 'phone') and admin.phone:
                            service.create_notification(
                                recipient=admin,
                                template=wa_template,
                                context_data=wa_context,
                                priority='urgent' if days_until_expiry <= 1 else 'high'
                            )
                except NotificationTemplate.DoesNotExist:
                    pass
                    
            transaction.on_commit(send_subscription_notifications)


