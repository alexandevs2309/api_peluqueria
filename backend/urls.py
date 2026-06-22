import os

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.settings_api.views import SystemSettingsRetrieveUpdateView, SystemSettingsResetView
from apps.utils.views import public_health_check


@require_http_methods(["GET"])
def health_check(request):
    checks = {}
    all_ok = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = f"error: {exc}"
        all_ok = False

    try:
        cache.set("healthz_ping", "pong", timeout=5)
        checks["cache"] = "ok" if cache.get("healthz_ping") == "pong" else "error: unexpected value"
        if checks["cache"] != "ok":
            all_ok = False
    except Exception as exc:
        checks["cache"] = f"error: {exc}"
        all_ok = False

    checks["app"] = "ok"
    return JsonResponse(
        {"status": "healthy" if all_ok else "degraded", "checks": checks},
        status=200 if all_ok else 503,
    )

def sentry_test(request):
    """Endpoint para probar Sentry - solo en DEBUG"""
    from django.conf import settings
    if not settings.DEBUG:
        return JsonResponse({"error": "Not available in production"}, status=403)
    
    # Generar error de prueba
    division_by_zero = 1 / 0
    return JsonResponse({"status": "This should not be reached"})


CRON_API_KEY = os.environ.get('CRON_API_KEY', '')
CRON_TASKS = {
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
    'check_trial_expirations': 'apps.subscriptions_api.tasks.check_trial_expirations',
    'auto_process_daily_absences': 'apps.employees_api.tasks.auto_process_daily_absences',
    'auto_checkout_end_of_day': 'apps.employees_api.tasks.auto_checkout_end_of_day',
    'send_subscription_expiry_warnings': 'apps.subscriptions_api.tasks.send_subscription_expiry_warnings',
}
CRON_GROUPS = {
    'frequent': {'mark_expired_appointments', 'notify_upcoming_appointments', 'check_expired_subscriptions'},
    'hourly': {'notify_upcoming_appointments', 'check_expired_subscriptions'},
    'daily': {
        'send_daily_reminders', 'send_appointment_reminders', 'daily_subscription_check',
        'send_trial_warnings', 'cleanup_expired_trials', 'daily_reconciliation',
        'check_trial_expirations', 'auto_process_daily_absences', 'auto_checkout_end_of_day',
        'send_subscription_expiry_warnings',
    },
    'weekly': {'cleanup_old_notifications'},
}


@require_http_methods(["GET"])
@csrf_exempt
def cron_run(request):
    """Ejecuta tareas programadas. Invocado por cron-job.org.
    Requiere header X-Cron-Key. Grupos: frequent, hourly, daily, weekly, all."""
    if not CRON_API_KEY:
        return JsonResponse({'error': 'CRON_API_KEY not configured'}, status=503)
    auth = request.META.get('HTTP_X_CRON_KEY', '')
    if not auth or auth != CRON_API_KEY:
        return JsonResponse({'error': 'Forbidden'}, status=403)

    task_name = request.GET.get('task', '')
    group = request.GET.get('group', '')

    if task_name:
        if task_name not in CRON_TASKS:
            return JsonResponse({'error': f'Unknown task: {task_name}'}, status=400)
        tasks_to_run = {task_name}
    elif group:
        if group == 'all':
            tasks_to_run = set(CRON_TASKS.keys())
        elif group not in CRON_GROUPS:
            return JsonResponse({'error': f'Unknown group: {group}'}, status=400)
        else:
            tasks_to_run = CRON_GROUPS[group]
    else:
        return JsonResponse({'error': 'Specify task= or group='}, status=400)

    from celery import current_app as celery_app
    from importlib import import_module

    results = {}
    for key in tasks_to_run:
        try:
            module_path, func_name = CRON_TASKS[key].rsplit('.', 1)
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

urlpatterns = [
    path('api/', include([
        path('auth/', include('apps.auth_api.urls')),
        path('roles/', include('apps.roles_api.urls')),
        path('clients/', include('apps.clients_api.urls')),
        path('appointments/', include('apps.appointments_api.urls')),
        path('services/', include('apps.services_api.urls')),
        path('employees/', include('apps.employees_api.urls')),
        path('pos/', include('apps.pos_api.urls')),
        path('inventory/', include('apps.inventory_api.urls')),
        path('reports/', include('apps.reports_api.urls')),
        path('subscriptions/', include('apps.subscriptions_api.urls')),
        path('tenants/', include('apps.tenants_api.urls')),
        path('billing/', include('apps.billing_api.urls')),
        path('payments/', include('apps.payments_api.urls')),
        path('settings/', include('apps.settings_api.urls')),
        path('system-settings/', SystemSettingsRetrieveUpdateView.as_view(), name='system-settings'),
        path('system-settings/reset/', SystemSettingsResetView.as_view(), name='system-settings-reset'),
        path('audit/', include('apps.audit_api.urls')),
        path('notifications/', include('apps.notifications_api.urls')),
        path('support/', include('apps.support_api.urls')),
        path('tutorials/', include('apps.tutorials_api.urls')),
        path('booking/', include('apps.booking_api.urls')),
        path('chatbot/', include('apps.chatbot_api.urls')),

        path("healthz/", health_check, name="health_check"),
        path("healthz/public/", public_health_check, name="public_health_check"),
        path("sentry-test/", sentry_test, name="sentry_test"),
        path("cron/run/", cron_run, name="cron_run"),
    ])),
]

if settings.DEBUG:
    urlpatterns += [
        path('', include('django_prometheus.urls')),
        path('admin/', admin.site.urls),
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
