from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model
from .models import AuditLog

User = get_user_model()

def migrate_existing_logs():
    """
    Función para migrar todos los logs existentes al nuevo sistema unificado
    """
    migrated_count = 0
    
    # Migrar LoginAudit
    try:
        from apps.auth_api.models import LoginAudit
        for log in LoginAudit.objects.all():
            AuditLog.objects.create(
                user=log.user,
                action='LOGIN' if log.successful else 'LOGIN_FAILED',
                description=f"Intento de login {'exitoso' if log.successful else 'fallido'}",
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                timestamp=log.timestamp,
                source='AUTH',
                extra_data={
                    'original_model': 'LoginAudit',
                    'original_id': log.id,
                    'successful': log.successful
                }
            )
            migrated_count += 1
    except ImportError:
        pass
    
    # Migrar AccessLog
    try:
        from apps.auth_api.models import AccessLog
        action_mapping = {
            'LOGIN': 'LOGIN',
            'LOGOUT': 'LOGOUT',
            'PASSWORD_CHANGE': 'PASSWORD_CHANGE',
            'ACTIVE_SESSIONS_VIEW': 'VIEW',
        }
        
        for log in AccessLog.objects.all():
            action = action_mapping.get(log.event_type, 'VIEW')
            AuditLog.objects.create(
                user=log.user,
                action=action,
                description=f"Evento: {log.event_type}",
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                timestamp=log.timestamp,
                source='AUTH',
                extra_data={
                    'original_model': 'AccessLog',
                    'original_id': log.id,
                    'event_type': log.event_type
                }
            )
            migrated_count += 1
    except ImportError:
        pass
    
    # Migrar AdminActionLog
    try:
        from apps.roles_api.models import AdminActionLog
        for log in AdminActionLog.objects.all():
            AuditLog.objects.create(
                user=log.user,
                action='ADMIN_ACTION',
                description=log.action,
                ip_address=log.ip_address,
                timestamp=log.timestamp,
                source='ROLES',
                extra_data={
                    'original_model': 'AdminActionLog',
                    'original_id': log.id
                }
            )
            migrated_count += 1
    except ImportError:
        pass
    
    # Migrar SettingAuditLog
    try:
        from apps.settings_api.models import SettingAuditLog
        for log in SettingAuditLog.objects.all():
            content_type = ContentType.objects.get_for_model(log.setting)
            AuditLog.objects.create(
                user=log.changed_by,
                action='SETTING_UPDATE',
                description=f"Configuración actualizada: {log.change_summary}",
                content_type=content_type,
                object_id=log.setting.id,
                timestamp=log.changed_at,
                source='SETTINGS',
                extra_data={
                    'original_model': 'SettingAuditLog',
                    'original_id': log.id,
                    'change_summary': log.change_summary
                }
            )
            migrated_count += 1
    except ImportError:
        pass
    
    # Migrar SubscriptionAuditLog
    try:
        from apps.subscriptions_api.models import SubscriptionAuditLog
        action_mapping = {
            'created': 'SUBSCRIPTION_CREATE',
            'updated': 'SUBSCRIPTION_UPDATE',
            'cancelled': 'SUBSCRIPTION_CANCEL',
            'renewed': 'SUBSCRIPTION_RENEW',
            'plan_changed': 'SUBSCRIPTION_UPDATE',
        }
        
        for log in SubscriptionAuditLog.objects.all():
            content_type = ContentType.objects.get_for_model(log.subscription)
            action = action_mapping.get(log.action, 'SUBSCRIPTION_UPDATE')
            
            AuditLog.objects.create(
                user=log.user,
                action=action,
                description=f"Suscripción {log.action}",
                content_type=content_type,
                object_id=log.subscription.id,
                timestamp=log.created_at,
                source='SUBSCRIPTIONS',
                extra_data={
                    'original_model': 'SubscriptionAuditLog',
                    'original_id': log.id,
                    'action': log.action
                }
            )
            migrated_count += 1
    except ImportError:
        pass
    
    return migrated_count

def create_audit_log(user, action, description, content_object=None, 
                    ip_address=None, user_agent='', source='SYSTEM', 
                    extra_data=None):
    """
    Función helper para crear logs de auditoría de forma unificada
    """
    kwargs = {
        'user': user,
        'action': action,
        'description': description,
        'ip_address': ip_address,
        'user_agent': user_agent or '',  # Asegurar que user_agent no sea None
        'source': source,
    }
    
    if content_object:
        # Para GenericForeignKey, necesitamos establecer content_type y object_id explícitamente
        try:
            from django.contrib.contenttypes.models import ContentType
            kwargs['content_type'] = ContentType.objects.get_for_model(content_object)
        except Exception:
            # Si la tabla contenttypes no existe aún (durante migraciones), saltar
            kwargs['content_type'] = None

        # Manejar diferentes tipos de objetos que pueden no tener un atributo 'id' estándar
        if hasattr(content_object, 'id'):
            kwargs['object_id'] = content_object.id
        elif hasattr(content_object, 'pk'):
            kwargs['object_id'] = content_object.pk
        else:
            # Si el objeto no tiene id ni pk, no podemos establecer object_id
            kwargs['object_id'] = None
    
    if extra_data:
        kwargs['extra_data'] = extra_data
    
    return AuditLog.objects.create(**kwargs)
