from rest_framework import generics, permissions, response, status, views

from apps.core.permissions import IsSuperAdmin
from apps.core.tenant_permissions import TenantPermissionByAction
from apps.tenants_api.base_viewsets import TenantScopedViewSet

from .models import Branch, SystemSettings
from .serializers import BranchSerializer, BranchWriteSerializer, SystemSettingsSerializer
from .utils import clear_system_config_cache, get_system_config


class PublicBrandingSettingsView(views.APIView):
    """Expose solo branding seguro para frontend público. Cacheado 5 min vía headers HTTP."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = []

    def get(self, request, *args, **kwargs):
        settings = get_system_config()
        platform_domain = (settings.platform_domain or "").strip()

        public_site_url = ""
        if platform_domain:
            public_site_url = platform_domain
            if not public_site_url.startswith(("http://", "https://")):
                scheme = "http" if "localhost" in public_site_url else "https"
                public_site_url = f"{scheme}://{public_site_url}"

        supported_languages = settings.supported_languages if isinstance(settings.supported_languages, list) else []

        return response.Response(
            {
                "platform_name": settings.platform_name,
                "support_email": settings.support_email,
                "platform_domain": platform_domain,
                "public_site_url": public_site_url,
                "supported_languages": supported_languages,
                "maintenance_mode": bool(settings.maintenance_mode),
            },
            status=status.HTTP_200_OK,
            headers={"Cache-Control": "public, max-age=300"},
        )


class BranchViewSet(TenantScopedViewSet):
    queryset = Branch.objects.all()
    pagination_class = None
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'settings_api.view_branch',
        'retrieve': 'settings_api.view_branch',
        'create': 'settings_api.add_branch',
        'update': 'settings_api.change_branch',
        'partial_update': 'settings_api.change_branch',
        'destroy': 'settings_api.delete_branch',
    }

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return BranchWriteSerializer
        return BranchSerializer

    def perform_create(self, serializer):
        super().perform_create(serializer)
        if serializer.instance.is_main:
            Branch.objects.filter(tenant=serializer.instance.tenant).exclude(
                pk=serializer.instance.pk
            ).update(is_main=False)


class SystemSettingsRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """Vista para obtener y actualizar configuraciones globales del sistema."""

    serializer_class = SystemSettingsSerializer
    permission_classes = [IsSuperAdmin]

    def get_object(self):
        return SystemSettings.get_settings()

    def get_permissions(self):
        return [IsSuperAdmin()]

    def perform_update(self, serializer):
        serializer.save()
        clear_system_config_cache()


class SystemSettingsResetView(views.APIView):
    """Vista para restablecer configuraciones a valores por defecto."""

    permission_classes = [IsSuperAdmin]

    def post(self, request, *args, **kwargs):
        SystemSettings.objects.all().delete()
        clear_system_config_cache()
        settings = SystemSettings.get_settings()
        serializer = SystemSettingsSerializer(settings)
        return response.Response(serializer.data, status=status.HTTP_200_OK)
