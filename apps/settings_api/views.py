from rest_framework import generics, permissions, parsers, views, response, status
from rest_framework.decorators import api_view, permission_classes
from .models import Setting, SettingAuditLog, Branch, SystemSettings
from .serializers import SettingSerializer, SettingExportSerializer, SettingAuditLogSerializer, BranchSerializer, SystemSettingsSerializer
from django.core.cache import cache
from django.db import transaction
from .utils import clear_system_config_cache
from .integration_service import IntegrationService

class SettingRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [parsers.MultiPartParser, parsers.JSONParser]

    def get_queryset(self):
        return super().get_queryset()

    def get_object(self):
        branch_id = self.request.query_params.get("branch")
        if not branch_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("El parámetro 'branch' es obligatorio.")
        key = f"setting_{branch_id or 'default'}"
        setting = cache.get(key)
        if not setting:
            setting = self.get_queryset().filter(branch_id=branch_id).first()
        if not setting:
            from rest_framework.exceptions import NotFound
            raise NotFound("Configuración no encontrada para la sucursal especificada.")
        cache.set(key, setting, 300)
        return setting
    
    def get(self, request, *args, **kwargs):
        branch_id = request.query_params.get("branch")
        if not branch_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("El parámetro 'branch' es obligatorio.")
        
        setting = self.get_queryset().filter(branch_id=branch_id).first()
        if not setting:
            return response.Response({"detail": "Configuración no encontrada"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(setting)
        return response.Response(serializer.data)

    def put(self, request, *args, **kwargs):
        print(f"\n=== PUT SETTINGS DEBUG ===")
        print(f"Query params: {request.query_params}")
        print(f"Request data: {request.data}")
        print(f"User: {request.user}")
        
        branch_id = request.query_params.get("branch")
        if not branch_id:
            print("ERROR: Missing branch parameter")
            from rest_framework.exceptions import ValidationError
            raise ValidationError("El parámetro 'branch' es obligatorio.")
        
        print(f"Branch ID: {branch_id}")
        
        # Verificar si existe la configuración
        setting = self.get_queryset().filter(branch_id=branch_id).first()
        print(f"Existing setting: {setting}")
        
        if setting:
            print("Updating existing setting")
            # Actualizar existente
            return self.update(request, *args, **kwargs)
        else:
            print("Creating new setting")
            # Crear nueva configuración
            serializer = self.get_serializer(data=request.data)
            print(f"Serializer valid: {serializer.is_valid()}")
            if not serializer.is_valid():
                print(f"Serializer errors: {serializer.errors}")
            serializer.is_valid(raise_exception=True)
            instance = serializer.save()
            
            SettingAuditLog.objects.create(
                setting=instance,
                changed_by=request.user,
                change_summary={"old": {}, "new": SettingExportSerializer(instance).data}
            )
            cache.delete(f"setting_{instance.branch_id or 'default'}")
            
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def perform_update(self, serializer):
        print(f"perform_update called")
        try:
            old_data = SettingExportSerializer(self.get_object()).data
            print(f"Old data retrieved")
            
            print(f"Serializer valid: {serializer.is_valid()}")
            if not serializer.is_valid():
                print(f"Serializer errors: {serializer.errors}")
                return
            
            instance = serializer.save()
            print(f"Instance saved: {instance}")
            
            SettingAuditLog.objects.create(
                setting=instance,
                changed_by=self.request.user,
                change_summary={"old": old_data, "new": SettingExportSerializer(instance).data}
            )
            print(f"Audit log created")
            
            cache.delete(f"setting_{instance.branch_id or 'default'}")
            print(f"Cache cleared")
        except Exception as e:
            print(f"Error in perform_update: {e}")
            import traceback
            traceback.print_exc()
            raise

class SettingExportView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, *args, **kwargs):
        branch_id = request.query_params.get("branch")
        setting = Setting.objects.filter(branch_id=branch_id).first()
        if not setting:
            return response.Response({"detail": "No encontrado"}, status=status.HTTP_404_NOT_FOUND)
        data = SettingExportSerializer(setting).data
        return response.Response(data)

class SettingImportView(views.APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, *args, **kwargs):
        data = request.data
        serializer = SettingExportSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        branch_id = data.get("branch")
        Setting.objects.filter(branch_id=branch_id).delete()
        setting = Setting.objects.create(**serializer.validated_data)
        return response.Response(SettingExportSerializer(setting).data)

class SettingAuditLogListView(generics.ListAPIView):
    queryset = SettingAuditLog.objects.all()
    serializer_class = SettingAuditLogSerializer
    permission_classes = [permissions.IsAdminUser]

class BranchListCreateView(generics.ListCreateAPIView):
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.tenant:
            return Branch.objects.filter(tenant=self.request.user.tenant)
        return Branch.objects.none()

class SettingListCreateView(generics.ListCreateAPIView):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [permissions.IsAdminUser]

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

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def branches_list(request):
    """Lista de sucursales del tenant"""
    if request.user.tenant:
        branches = Branch.objects.filter(tenant=request.user.tenant)
        return response.Response([{
            'id': branch.id,
            'name': branch.name,
            'address': branch.address or 'Dirección no configurada',
            'is_main': branch.is_main,
            'is_active': branch.is_active
        } for branch in branches])
    return response.Response([])
