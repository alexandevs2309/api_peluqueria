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