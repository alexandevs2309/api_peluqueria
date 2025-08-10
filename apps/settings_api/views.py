from rest_framework import generics, permissions, parsers, views, response, status
from .models import Setting, SettingAuditLog, Branch
from .serializers import SettingSerializer, SettingExportSerializer, SettingAuditLogSerializer, BranchSerializer
from django.core.cache import cache
from django.db import transaction

class SettingRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [permissions.IsAdminUser]
    parser_classes = [parsers.MultiPartParser, parsers.JSONParser]

    def get_object(self):
        branch_id = self.request.query_params.get("branch")
        if not branch_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError("El parámetro 'branch' es obligatorio.")
        key = f"setting_{branch_id or 'default'}"
        setting = cache.get(key)
        if not setting:
            setting = Setting.objects.filter(branch_id=branch_id).first()
        if not setting:
                from rest_framework.exceptions import NotFound
                raise NotFound("Configuración no encontrada para la sucursal especificada.")
        cache.set(key, setting, 300)
        return setting

    @transaction.atomic
    def perform_update(self, serializer):
        old_data = SettingExportSerializer(self.get_object()).data
        instance = serializer.save()
        SettingAuditLog.objects.create(
            setting=instance,
            changed_by=self.request.user,
            change_summary={"old": old_data, "new": SettingExportSerializer(instance).data}
        )
        cache.delete(f"setting_{instance.branch_id or 'default'}")

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
    permission_classes = [permissions.IsAdminUser]

class SettingListCreateView(generics.ListCreateAPIView):
    queryset = Setting.objects.all()
    serializer_class = SettingSerializer
    permission_classes = [permissions.IsAdminUser]
