from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from apps.billing_api.metrics import FinancialMetrics


@api_view(['GET'])
@permission_classes([IsAdminUser])
def metrics_dashboard(request):
    """Dashboard de métricas en tiempo real"""
    
    # Métricas de base de datos
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active';")
            active_connections = cursor.fetchone()[0]
    except Exception:
        active_connections = 0
    
    # Métricas financieras
    financial_metrics = FinancialMetrics.get_metrics_summary()
    
    payments_success = financial_metrics['payments']['success_today']
    payments_failure = financial_metrics['payments']['failure_today']
    total_payments = payments_success + payments_failure
    
    error_rate = (payments_failure / total_payments * 100) if total_payments > 0 else 0
    
    # Métricas de Celery
    celery_stats = get_celery_stats()
    
    return Response({
        'timestamp': timezone.now().isoformat(),
        'database': {
            'active_connections': active_connections,
        },
        'financial': {
            'mrr': financial_metrics['mrr']['current'],
            'mrr_avg_7d': financial_metrics['mrr']['avg_7d'],
            'payments_success_today': payments_success,
            'payments_failure_today': payments_failure,
            'error_rate': round(error_rate, 2),
        },
        'celery': celery_stats,
    })


def get_celery_stats():
    """Obtener estadísticas de Celery"""
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        
        active_tasks = inspect.active() or {}
        scheduled_tasks = inspect.scheduled() or {}
        
        return {
            'active_tasks': sum(len(tasks) for tasks in active_tasks.values()),
            'scheduled_tasks': sum(len(tasks) for tasks in scheduled_tasks.values()),
            'workers': len(active_tasks),
        }
    except Exception:
        return {
            'active_tasks': 0,
            'scheduled_tasks': 0,
            'workers': 0,
            'error': 'Celery not available'
        }


@api_view(['GET'])
@permission_classes([IsAdminUser])
def health_check(request):
    """Health check completo del sistema"""
    
    health = {
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'checks': {}
    }
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health['checks']['database'] = 'ok'
    except Exception as e:
        health['checks']['database'] = f'error: {str(e)}'
        health['status'] = 'unhealthy'
    
    # Check cache
    try:
        cache.set('health_check', 'ok', 10)
        if cache.get('health_check') == 'ok':
            health['checks']['cache'] = 'ok'
        else:
            health['checks']['cache'] = 'error'
            health['status'] = 'degraded'
    except Exception as e:
        health['checks']['cache'] = f'error: {str(e)}'
        health['status'] = 'degraded'
    
    # Check Celery
    celery_stats = get_celery_stats()
    if 'error' in celery_stats:
        health['checks']['celery'] = 'error'
        health['status'] = 'degraded'
    else:
        health['checks']['celery'] = 'ok'
    
    status_code = 200 if health['status'] == 'healthy' else 503
    return Response(health, status=status_code)
