from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import redis
import time
from celery import current_app
from datetime import datetime, timedelta

def health_check(request):
    """
    Health endpoint completo para monitoreo
    RPO: 24 horas (backup diario)
    RTO: 15 minutos (tiempo estimado de restore + restart)
    """
    start_time = time.time()
    status = "healthy"
    checks = {}
    
    # 1. Database Check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = {"status": "ok", "response_time_ms": round((time.time() - db_start) * 1000, 2)}
    except Exception as e:
        checks["database"] = {"status": "error", "error": str(e)}
        status = "unhealthy"
    
    # 2. Redis Check
    db_start = time.time()
    try:
        cache.set("health_check", "ok", 30)
        result = cache.get("health_check")
        if result == "ok":
            checks["redis"] = {"status": "ok", "response_time_ms": round((time.time() - db_start) * 1000, 2)}
        else:
            checks["redis"] = {"status": "error", "error": "Cache test failed"}
            status = "unhealthy"
    except Exception as e:
        checks["redis"] = {"status": "error", "error": str(e)}
        status = "unhealthy"
    
    # 3. Celery Check
    celery_start = time.time()
    try:
        # Verificar workers activos
        inspect = current_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            worker_count = len(active_workers)
            checks["celery"] = {
                "status": "ok", 
                "workers": worker_count,
                "response_time_ms": round((time.time() - celery_start) * 1000, 2)
            }
        else:
            checks["celery"] = {"status": "warning", "workers": 0, "message": "No active workers"}
            if status == "healthy":
                status = "degraded"
    except Exception as e:
        checks["celery"] = {"status": "error", "error": str(e)}
        status = "unhealthy"
    
    # 4. Disk Space Check
    try:
        import shutil
        disk_usage = shutil.disk_usage("/")
        free_gb = disk_usage.free / (1024**3)
        total_gb = disk_usage.total / (1024**3)
        usage_percent = ((total_gb - free_gb) / total_gb) * 100
        
        if usage_percent > 90:
            checks["disk"] = {"status": "critical", "usage_percent": round(usage_percent, 1), "free_gb": round(free_gb, 1)}
            status = "unhealthy"
        elif usage_percent > 80:
            checks["disk"] = {"status": "warning", "usage_percent": round(usage_percent, 1), "free_gb": round(free_gb, 1)}
            if status == "healthy":
                status = "degraded"
        else:
            checks["disk"] = {"status": "ok", "usage_percent": round(usage_percent, 1), "free_gb": round(free_gb, 1)}
    except Exception as e:
        checks["disk"] = {"status": "error", "error": str(e)}
    
    response_data = {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "response_time_ms": round((time.time() - start_time) * 1000, 2),
        "checks": checks,
        "rpo_hours": 24,  # Recovery Point Objective
        "rto_minutes": 15,  # Recovery Time Objective
        "version": getattr(settings, 'APP_VERSION', '1.0.0')
    }
    
    # Status code según estado
    status_codes = {
        "healthy": 200,
        "degraded": 200,
        "unhealthy": 503
    }
    
    return JsonResponse(response_data, status=status_codes.get(status, 503))


import os
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

CRON_API_KEY = os.environ.get('CRON_API_KEY', '')
TASKS_REGISTRY = {
    'mark_expired_appointments': 'apps.notifications_api.tasks.mark_expired_appointments',
    'send_daily_reminders': 'apps.notifications_api.tasks.send_daily_appointment_reminders',
    'notify_upcoming_appointments': 'apps.notifications_api.tasks.notify_upcoming_appointments',
    'send_appointment_reminders': 'apps.notifications_api.tasks.send_appointment_reminders',
    'cleanup_old_notifications': 'apps.notifications_api.tasks.cleanup_old_notifications',
    'check_expired_subscriptions': 'apps.subscriptions_api.tasks.check_expired_subscriptions',
    'cleanup_expired_trials': 'apps.subscriptions_api.tasks.cleanup_expired_trials',
    'send_trial_warnings': 'apps.subscriptions_api.tasks.send_trial_expiration_warnings',
    'daily_subscription_check': 'apps.subscriptions_api.tasks.daily_subscription_check',
    'daily_reconciliation': 'apps.billing_api.tasks.daily_financial_reconciliation',
}

ALL_TASK_KEYS = {
    'mark_expired_appointments',
    'send_daily_reminders',
    'notify_upcoming_appointments',
    'send_appointment_reminders',
    'check_expired_subscriptions',
    'daily_subscription_check',
}

DAILY_TASK_KEYS = {
    'send_daily_reminders',
    'send_appointment_reminders',
    'daily_subscription_check',
    'send_trial_warnings',
    'cleanup_expired_trials',
    'daily_reconciliation',
}

HOURLY_TASK_KEYS = {
    'notify_upcoming_appointments',
    'check_expired_subscriptions',
}

WEEKLY_TASK_KEYS = {
    'cleanup_old_notifications',
}

TASK_GROUPS = {
    'all': ALL_TASK_KEYS | DAILY_TASK_KEYS | HOURLY_TASK_KEYS | WEEKLY_TASK_KEYS,
    'frequent': ALL_TASK_KEYS,
    'daily': DAILY_TASK_KEYS,
    'hourly': HOURLY_TASK_KEYS,
    'weekly': WEEKLY_TASK_KEYS,
}


@require_http_methods(["GET"])
@csrf_exempt
def cron_run(request):
    """
    Ejecuta tareas programadas (Celery Beat) de forma síncrona.
    Diseñado para ser invocado por un cron externo (cron-job.org, Render Cron, etc.).

    Requiere header `X-Cron-Key` igual a CRON_API_KEY.

    Parámetros query:
      - group: 'frequent' (cada 15min), 'hourly', 'daily', 'weekly', 'all'
      - task: nombre individual de tarea (ej: mark_expired_appointments)

    Ejemplos:
      GET /api/cron/run/?group=frequent       # cada 15 min
      GET /api/cron/run/?group=hourly          # cada hora
      GET /api/cron/run/?group=daily           # diario
      GET /api/cron/run/?task=mark_expired_appointments  # tarea específica
    """
    if CRON_API_KEY:
        auth = request.META.get('HTTP_X_CRON_KEY', '')
        if auth != CRON_API_KEY:
            return JsonResponse({'error': 'Forbidden'}, status=403)

    task_name = request.GET.get('task', '')
    group = request.GET.get('group', '')

    if task_name:
        if task_name not in TASKS_REGISTRY:
            return JsonResponse({'error': f'Unknown task: {task_name}'}, status=400)
        tasks_to_run = {task_name}
    elif group:
        if group not in TASK_GROUPS:
            return JsonResponse({'error': f'Unknown group: {group}'}, status=400)
        tasks_to_run = TASK_GROUPS[group]
    else:
        return JsonResponse({'error': 'Specify task= or group='}, status=400)

    from celery import current_app as celery_app
    from importlib import import_module

    results = {}
    for key in tasks_to_run:
        try:
            module_path, func_name = TASKS_REGISTRY[key].rsplit('.', 1)
            module = import_module(module_path)
            task_func = getattr(module, func_name)
            result = task_func.delay()
            try:
                task_result = result.get(timeout=120)
            except Exception:
                task_result = 'completed (no result)'
            results[key] = {'status': 'ok', 'result': task_result}
        except Exception as e:
            results[key] = {'status': 'error', 'error': str(e)}

    all_ok = all(r['status'] == 'ok' for r in results.values())
    return JsonResponse({
        'status': 'ok' if all_ok else 'partial',
        'results': results,
    })


def metrics(request):
    """Endpoint de métricas básicas para monitoreo"""
    try:
        # Métricas de base de datos
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    n_tup_ins as inserts,
                    n_tup_upd as updates,
                    n_tup_del as deletes
                FROM pg_stat_user_tables 
                WHERE schemaname = 'public'
                ORDER BY n_tup_ins + n_tup_upd + n_tup_del DESC
                LIMIT 10
            """)
            db_stats = cursor.fetchall()
        
        # Métricas de Redis
        try:
            r = redis.Redis.from_url(settings.CACHES['default']['LOCATION'])
            redis_info = r.info()
            redis_stats = {
                "used_memory_mb": round(redis_info['used_memory'] / (1024*1024), 2),
                "connected_clients": redis_info['connected_clients'],
                "total_commands_processed": redis_info['total_commands_processed']
            }
        except:
            redis_stats = {"error": "Redis not available"}
        
        return JsonResponse({
            "database_activity": [
                {"table": f"{row[0]}.{row[1]}", "inserts": row[2], "updates": row[3], "deletes": row[4]}
                for row in db_stats
            ],
            "redis": redis_stats,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)