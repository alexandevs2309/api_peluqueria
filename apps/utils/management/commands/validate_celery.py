"""
Validador de Celery para producción
apps/utils/celery_validator.py
"""
from celery import Celery
from django.core.management.base import BaseCommand
from django.conf import settings
import redis
import time


class CeleryProductionValidator:
    """Validador de Celery para entorno de producción."""
    
    def __init__(self):
        self.app = Celery('saas_peluquerias')
        self.app.config_from_object('django.conf:settings', namespace='CELERY')
        self.issues = []
    
    def validate_broker_connection(self):
        """Validar conexión con Redis broker."""
        try:
            r = redis.from_url(settings.CELERY_BROKER_URL)
            r.ping()
            print("✅ Conexión con Redis broker: OK")
        except Exception as e:
            self.issues.append(f"❌ Redis broker: {str(e)}")
    
    def validate_workers(self):
        """Validar que hay workers activos."""
        try:
            inspect = self.app.control.inspect()
            active_workers = inspect.active()
            
            if not active_workers:
                self.issues.append("❌ No hay workers de Celery activos")
                return
            
            worker_count = len(active_workers)
            print(f"✅ Workers activos: {worker_count}")
            
            # Verificar que workers están procesando
            for worker, tasks in active_workers.items():
                print(f"  - {worker}: {len(tasks)} tareas activas")
                
        except Exception as e:
            self.issues.append(f"❌ Error verificando workers: {str(e)}")
    
    def validate_beat_schedule(self):
        """Validar configuración de Celery Beat."""
        beat_schedule = getattr(settings, 'CELERY_BEAT_SCHEDULE', {})
        
        if not beat_schedule:
            self.issues.append("⚠️ No hay tareas programadas en CELERY_BEAT_SCHEDULE")
            return
        
        print(f"✅ Tareas programadas: {len(beat_schedule)}")
        
        # Validar tareas críticas
        critical_tasks = [
            'cleanup-expired-trials',
            'check-expired-subscriptions',
            'send-appointment-reminders'
        ]
        
        for task_name in critical_tasks:
            if task_name not in beat_schedule:
                self.issues.append(f"⚠️ Tarea crítica faltante: {task_name}")
            else:
                print(f"  ✅ {task_name}: configurada")
    
    def test_task_execution(self):
        """Test de ejecución de tarea simple."""
        try:
            from apps.notifications_api.tasks import test_task
            
            # Enviar tarea de prueba
            result = test_task.delay("production_test")
            
            # Esperar resultado (máximo 10 segundos)
            for _ in range(10):
                if result.ready():
                    break
                time.sleep(1)
            
            if result.ready() and result.successful():
                print("✅ Test de ejecución de tarea: OK")
            else:
                self.issues.append("❌ Tarea de prueba falló o timeout")
                
        except Exception as e:
            self.issues.append(f"❌ Error en test de tarea: {str(e)}")
    
    def validate_task_idempotency(self):
        """Validar que tareas críticas son idempotentes."""
        # Lista de tareas que DEBEN ser idempotentes
        idempotent_tasks = [
            'apps.subscriptions_api.tasks.cleanup_expired_trials',
            'apps.subscriptions_api.tasks.check_expired_subscriptions',
            'apps.notifications_api.tasks.send_appointment_reminders',
        ]
        
        print("🔍 Validando idempotencia de tareas críticas...")
        
        for task_path in idempotent_tasks:
            # Verificar que la tarea tiene decorador @shared_task(bind=True)
            # y maneja duplicados correctamente
            print(f"  ⚠️ MANUAL: Verificar idempotencia de {task_path}")
    
    def get_monitoring_recommendations(self):
        """Recomendar qué monitorear en producción."""
        return {
            'ALERTAS_CRÍTICAS': [
                'Workers de Celery caídos (0 workers activos)',
                'Cola de tareas creciendo (>1000 tareas pendientes)',
                'Tareas fallando repetidamente (>10 fallos/hora)',
                'Beat scheduler no ejecutando tareas'
            ],
            'MÉTRICAS_A_SEGUIR': [
                'Número de workers activos',
                'Tareas procesadas por minuto',
                'Tiempo promedio de ejecución por tarea',
                'Tareas en cola por tipo',
                'Tasa de fallos por tarea'
            ],
            'COMANDOS_ÚTILES': [
                'celery -A backend inspect active',
                'celery -A backend inspect stats',
                'celery -A backend events',
                'celery -A backend control pool_grow N'
            ]
        }
    
    def run_full_validation(self):
        """Ejecutar validación completa."""
        print("🔍 Validando Celery para producción...\n")
        
        self.validate_broker_connection()
        self.validate_workers()
        self.validate_beat_schedule()
        self.test_task_execution()
        self.validate_task_idempotency()
        
        if self.issues:
            print("\n❌ PROBLEMAS ENCONTRADOS:")
            for issue in self.issues:
                print(f"  {issue}")
            return False
        else:
            print("\n✅ Celery validado correctamente para producción")
            return True


# Tarea de prueba simple
from celery import shared_task

@shared_task(bind=True)
def test_task(self, message):
    """Tarea simple para testing."""
    return f"Test completado: {message}"


# Comando Django para validación
class Command(BaseCommand):
    help = 'Validar configuración de Celery para producción'
    
    def handle(self, *args, **options):
        validator = CeleryProductionValidator()
        
        if validator.run_full_validation():
            self.stdout.write(
                self.style.SUCCESS('✅ Celery listo para producción')
            )
        else:
            self.stdout.write(
                self.style.ERROR('❌ Celery NO listo para producción')
            )
            
        # Mostrar recomendaciones de monitoreo
        recommendations = validator.get_monitoring_recommendations()
        
        self.stdout.write('\n📊 RECOMENDACIONES DE MONITOREO:')
        for category, items in recommendations.items():
            self.stdout.write(f'\n{category}:')
            for item in items:
                self.stdout.write(f'  • {item}')