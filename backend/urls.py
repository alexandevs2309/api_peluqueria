from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

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
    ])),

]