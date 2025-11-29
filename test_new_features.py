#!/usr/bin/env python
"""
Script para probar las nuevas funcionalidades del API
"""
import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

def test_reports_endpoints():
    """Probar endpoints de reportes"""
    print("🔍 Probando endpoints de reportes...")
    
    from django.test import Client
    from apps.auth_api.models import User
    from apps.tenants_api.models import Tenant
    
    # Crear cliente de prueba
    client = Client()
    
    # Crear usuario de prueba si no existe
    try:
        user = User.objects.get(email='test@example.com')
    except User.DoesNotExist:
        tenant = Tenant.objects.first()
        user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            tenant=tenant
        )
    
    # Login
    client.force_login(user)
    
    # Probar endpoints
    endpoints = [
        '/api/reports/',
        '/api/reports/kpi/',
        '/api/reports/calendar-data/?start=2024-01-01T00:00:00Z&end=2024-12-31T23:59:59Z',
        '/api/reports/services-performance/',
        '/api/reports/client-analytics/',
    ]
    
    for endpoint in endpoints:
        try:
            response = client.get(endpoint)
            status = "✅" if response.status_code == 200 else "❌"
            print(f"{status} {endpoint} - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - Error: {str(e)}")

def test_notifications_system():
    """Probar sistema de notificaciones"""
    print("\n📧 Probando sistema de notificaciones...")
    
    from apps.notifications_api.models import NotificationTemplate
    from apps.notifications_api.services import NotificationService
    from apps.auth_api.models import User
    
    # Crear templates si no existen
    from django.core.management import call_command
    try:
        call_command('create_notification_templates')
        print("✅ Templates de notificación creados")
    except Exception as e:
        print(f"⚠️ Templates: {str(e)}")
    
    # Probar servicio de notificaciones
    try:
        user = User.objects.first()
        template = NotificationTemplate.objects.filter(is_active=True).first()
        
        if user and template:
            service = NotificationService()
            notification = service.create_notification(
                recipient=user,
                template=template,
                context_data={'test': 'value'}
            )
            print(f"✅ Notificación creada: {notification.id}")
        else:
            print("⚠️ No hay usuarios o templates para probar")
    except Exception as e:
        print(f"❌ Error creando notificación: {str(e)}")

def test_appointments_calendar():
    """Probar endpoints de calendario"""
    print("\n📅 Probando endpoints de calendario...")
    
    from django.test import Client
    from apps.auth_api.models import User
    
    client = Client()
    user = User.objects.first()
    
    if user:
        client.force_login(user)
        
        endpoints = [
            '/api/appointments/calendar-events/?start=2024-01-01T00:00:00Z&end=2024-12-31T23:59:59Z',
            '/api/appointments/appointments/availability/?stylist_id=1&date=2024-12-01',
        ]
        
        for endpoint in endpoints:
            try:
                response = client.get(endpoint)
                status = "✅" if response.status_code in [200, 400] else "❌"  # 400 es OK si no hay datos
                print(f"{status} {endpoint} - Status: {response.status_code}")
            except Exception as e:
                print(f"❌ {endpoint} - Error: {str(e)}")
    else:
        print("⚠️ No hay usuarios para probar")

def test_database_migrations():
    """Verificar que las migraciones están al día"""
    print("\n🗄️ Verificando migraciones...")
    
    from django.core.management import call_command
    from io import StringIO
    
    try:
        # Verificar migraciones pendientes
        out = StringIO()
        call_command('showmigrations', '--plan', stdout=out)
        output = out.getvalue()
        
        if '[ ]' in output:
            print("⚠️ Hay migraciones pendientes")
            print("Ejecuta: python manage.py migrate")
        else:
            print("✅ Todas las migraciones están aplicadas")
    except Exception as e:
        print(f"❌ Error verificando migraciones: {str(e)}")

def test_celery_tasks():
    """Probar tareas de Celery"""
    print("\n⚙️ Probando tareas de Celery...")
    
    try:
        from apps.notifications_api.tasks import process_scheduled_notifications
        
        # Probar tarea (sin ejecutar realmente)
        task_name = process_scheduled_notifications.name
        print(f"✅ Tarea registrada: {task_name}")
        
        # Verificar que las tareas están en CELERY_BEAT_SCHEDULE
        from django.conf import settings
        schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
        
        expected_tasks = [
            'send-appointment-reminders',
            'process-scheduled-notifications',
            'cleanup-old-notifications'
        ]
        
        for task in expected_tasks:
            if task in schedule:
                print(f"✅ Tarea programada: {task}")
            else:
                print(f"❌ Tarea faltante: {task}")
                
    except Exception as e:
        print(f"❌ Error probando Celery: {str(e)}")

def main():
    """Ejecutar todas las pruebas"""
    print("🚀 Iniciando pruebas de nuevas funcionalidades...\n")
    
    test_database_migrations()
    test_reports_endpoints()
    test_notifications_system()
    test_appointments_calendar()
    test_celery_tasks()
    
    print("\n✨ Pruebas completadas!")
    print("\n📋 Próximos pasos:")
    print("1. Ejecutar migraciones si hay pendientes: python manage.py migrate")
    print("2. Crear templates: python manage.py create_notification_templates")
    print("3. Probar endpoints desde el frontend")
    print("4. Configurar Celery para tareas automáticas")

if __name__ == '__main__':
    main()