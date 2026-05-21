"""
============================================================
FIX 11: apps/settings_api/ — RBAC en SystemSettings y BarbershopSettings
PROBLEMA (de VULNERABILITIES_TABLE.csv):
  - SystemSettingsRetrieveUpdateView: Solo IsAuthenticated
  - BarbershopSettingsViewSet: Solo IsAuthenticated
  → Cualquier empleado puede ver y modificar la config del negocio.

INSTRUCCIÓN: Localizar ambas clases en settings_api/views.py y
             settings_api/barbershop_views.py y aplicar los cambios.
============================================================
"""

# ---- settings_api/views.py ----
# ANTES:
#   class SystemSettingsRetrieveUpdateView(generics.RetrieveUpdateAPIView):
#       permission_classes = [IsAuthenticated]

# DESPUÉS:
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.core.tenant_permissions import TenantPermissionByAction


class SystemSettingsRetrieveUpdateView(APIView):
    """
    Configuración global del sistema del tenant.
    GET → Solo roles con view_settings (Manager, Client-Admin).
    PUT/PATCH → Solo Client-Admin.
    """
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'GET':   'settings_api.view_systemsettings',
        'PUT':   'settings_api.change_systemsettings',
        'PATCH': 'settings_api.change_systemsettings',
    }

    def get_object(self):
        from .models import SystemSettings
        tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
        obj, _ = SystemSettings.objects.get_or_create(tenant=tenant)
        return obj

    def get(self, request, *args, **kwargs):
        from .serializers import SystemSettingsSerializer
        obj = self.get_object()
        serializer = SystemSettingsSerializer(obj)
        return Response(serializer.data)

    def put(self, request, *args, **kwargs):
        from .serializers import SystemSettingsSerializer
        obj = self.get_object()
        serializer = SystemSettingsSerializer(obj, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def patch(self, request, *args, **kwargs):
        from .serializers import SystemSettingsSerializer
        obj = self.get_object()
        serializer = SystemSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ---- settings_api/barbershop_views.py ----
# ANTES:
#   class BarbershopSettingsViewSet(viewsets.ModelViewSet):
#       permission_classes = [IsAuthenticated]
#       ...

# DESPUÉS: Agregar permission_classes y permission_map:

from apps.tenants_api.base_viewsets import TenantScopedViewSet


class BarbershopSettingsViewSet(TenantScopedViewSet):
    """
    Configuración de la barbería/salón del tenant.
    Modificar solo para Client-Admin.
    Leer para Manager y Client-Admin.
    """
    # queryset y serializer_class se mantienen igual que el original

    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list':           'settings_api.view_barbershopsettings',
        'retrieve':       'settings_api.view_barbershopsettings',
        'create':         'settings_api.add_barbershopsettings',
        'update':         'settings_api.change_barbershopsettings',
        'partial_update': 'settings_api.change_barbershopsettings',
        'destroy':        'settings_api.delete_barbershopsettings',
        # Actions custom — si existen en el viewset original:
        'upload_logo':    'settings_api.change_barbershopsettings',
        'delete_logo':    'settings_api.change_barbershopsettings',
    }
    # Resto del viewset sin cambios


"""
============================================================
FIX 11b: Migración para permisos de settings_api
Los permisos Django de settings_api se auto-generan con makemigrations/migrate
si los models tienen Meta.default_permissions = ('view', 'add', 'change', 'delete').
Verificar con:

python manage.py shell -c "
from django.contrib.auth.models import Permission
perms = Permission.objects.filter(content_type__app_label='settings_api')
print([p.codename for p in perms])
"

Si faltan permisos custom (upload_logo, etc.), crear con RunPython en migración.
============================================================
"""
