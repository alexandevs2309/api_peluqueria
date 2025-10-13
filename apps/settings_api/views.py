from rest_framework import generics, permissions, views, response, status
from .models import SystemSettings
from .serializers import SystemSettingsSerializer
from django.core.cache import cache
from django.db import transaction
from .utils import clear_system_config_cache
from .integration_service import IntegrationService



class SystemSettingsRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """Vista para obtener y actualizar configuraciones globales del sistema"""
    serializer_class = SystemSettingsSerializer
    permission_classes = [permissions.IsAdminUser]

    def get_object(self):
        return SystemSettings.get_settings()
    
    def perform_update(self, serializer):
        serializer.save()
        clear_system_config_cache()

class SystemSettingsResetView(views.APIView):
    """Vista para restablecer configuraciones a valores por defecto"""
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, *args, **kwargs):
        # Eliminar configuración existente y crear una nueva con valores por defecto
        SystemSettings.objects.all().delete()
        clear_system_config_cache()
        settings = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings)
        return response.Response(serializer.data, status=status.HTTP_200_OK)


