#!/usr/bin/env python
import os
import django
import sys

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.contrib.contenttypes.models import ContentType
from apps.audit_api.models import AuditLog

def migrate_existing_audit_logs():
    """
    Migrate existing audit logs to set content_type and object_id correctly
    """
    logs_migrated = 0
    
    # Get all logs where content_type is null but should have a content_object
    logs_to_migrate = AuditLog.objects.filter(content_type__isnull=True)
    
    for log in logs_to_migrate:
        # Try to determine content_type and object_id from extra_data
        if log.extra_data and 'original_model' in log.extra_data:
            try:
                model_name = log.extra_data['original_model']
                object_id = log.extra_data.get('original_id')
                
                if model_name and object_id:
                    # Map model names to actual models
                    model_mapping = {
                        'LoginAudit': 'auth_api.LoginAudit',
                        'AccessLog': 'auth_api.AccessLog',
                        'AdminActionLog': 'roles_api.AdminActionLog',
                        'SettingAuditLog': 'settings_api.SettingAuditLog',
                        'SubscriptionAuditLog': 'subscriptions_api.SubscriptionAuditLog',
                    }
                    
                    if model_name in model_mapping:
                        app_label, model_name = model_mapping[model_name].split('.')
                        content_type = ContentType.objects.get(app_label=app_label, model=model_name.lower())
                        
                        log.content_type = content_type
                        log.object_id = object_id
                        log.save()
                        logs_migrated += 1
                        print(f"Migrated log {log.id}: {model_name} - {object_id}")
                        
            except Exception as e:
                print(f"Error migrating log {log.id}: {e}")
                continue
    
    print(f"Migrated {logs_migrated} audit logs")
    
    # For logs that can't be migrated, set content_type_name manually
    logs_without_content = AuditLog.objects.filter(content_type__isnull=True)
    for log in logs_without_content:
        if log.source == 'AUTH' and log.action in ['LOGIN', 'LOGIN_FAILED']:
            log.content_type_name = 'Authentication'
            log.save()
        elif log.source == 'SYSTEM':
            log.content_type_name = 'System'
            log.save()
        print(f"Set content_type_name for log {log.id}: {log.content_type_name}")

if __name__ == '__main__':
    migrate_existing_audit_logs()
