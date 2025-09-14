from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.http import require_http_methods

from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.settings_api.views import SystemSettingsRetrieveUpdateView, SystemSettingsResetView

@require_http_methods(["GET"])
@cache_page(60)
def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include([
        path('auth/', include('apps.auth_api.urls')),
        path('roles/', include('apps.roles_api.urls')),
        path('schema/', SpectacularAPIView.as_view(), name='schema'),
        path('docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
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
        path('users/', include('apps.users_api.urls')),
        path('audit/', include('apps.audit_api.urls')),
        path('notifications/', include('apps.notifications_api.urls')),

        path("healthz/", health_check, name="health_check"),
    ])),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)