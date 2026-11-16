from rest_framework import viewsets, permissions, decorators, response, status, serializers
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from apps.core.permissions import IsSuperAdmin
from .models import Tenant
from .serializers import TenantSerializer, TenantLocaleSerializer
from django.contrib.contenttypes.models import ContentType
from apps.audit_api.models import AuditLog
from apps.settings_api.utils import validate_tenant_limit
User = get_user_model()

class TenantViewSet(viewsets.ModelViewSet):
    """
    ViewSet para manejar tenants:
    - Activar/desactivar
    - Obtener estadísticas
    - Registrar auditoría
    """
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [IsSuperAdmin]
    pagination_class = None
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_permissions(self):
        # Permitir acceso autenticado para endpoints del tenant actual.
        if self.action in ['subscription_status', 'locale', 'current']:
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    def get_queryset(self):
        # ✅ ESTANDARIZADO: Usar is_superuser en lugar de roles
        if self.request.user.is_superuser:
            return Tenant.objects.filter(deleted_at__isnull=True)
        # Otros usuarios no tienen acceso
        return Tenant.objects.none()

    def _create_audit_log(self, user, action, target):
        AuditLog.objects.create(
            user=user,
            action=action,
            description=f"{action} tenant: {target.name}",
            content_type=ContentType.objects.get_for_model(target),
            object_id=target.id,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            source='SYSTEM'
        )

    def perform_create(self, serializer):
        if not validate_tenant_limit():
            raise serializers.ValidationError({
                'error': 'Límite de clientes alcanzado',
                'message': 'No se pueden crear más clientes. Contacte al administrador.'
            })
        tenant = serializer.save(owner=self.request.user)

        AuditLog.objects.create(
            user=self.request.user,
            action='CREATE',
            description=f"Creó un nuevo tenant: {tenant.name}",
            content_type=ContentType.objects.get_for_model(tenant),
            object_id=tenant.id,
            ip_address=self.request.META.get('REMOTE_ADDR'),
            user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
            source='SYSTEM',
            extra_data={
                'tenant_name': tenant.name,
                'owner_id': tenant.owner.id if tenant.owner else None
            }
    )
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete de tenant"""
        tenant = self.get_object()
        tenant.soft_delete()
        
        AuditLog.objects.create(
            user=request.user,
            action='DELETE',
            description=f"Eliminó tenant: {tenant.name}",
            content_type=ContentType.objects.get_for_model(tenant),
            object_id=tenant.id,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            source='SYSTEM'
        )
        
        return response.Response(status=status.HTTP_204_NO_CONTENT)

    @decorators.action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        tenant = self.get_object()
        if tenant.is_active:
            return response.Response(
                {"status": "tenant already active"},
                status=status.HTTP_400_BAD_REQUEST
            )
        tenant.is_active = True
        tenant.save()
        self._create_audit_log(request.user, "Activated tenant", tenant)
        serializer = self.get_serializer(tenant)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        tenant = self.get_object()
        if not tenant.is_active:
            return response.Response(
                {"status": "tenant already inactive"},
                status=status.HTTP_400_BAD_REQUEST
            )
        tenant.is_active = False
        tenant.save()
        self._create_audit_log(request.user, "Deactivated tenant", tenant)
        serializer = self.get_serializer(tenant)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=["post"])
    def suspend(self, request, pk=None):
        tenant = self.get_object()
        reason = request.data.get("reason", "").strip()

        if tenant.subscription_status == "suspended":
            return response.Response(
                {"status": "tenant already suspended"},
                status=status.HTTP_400_BAD_REQUEST
            )

        tenant.suspend_subscription(save=True)

        self._create_audit_log(
            request.user,
            f"Suspended tenant ({reason})" if reason else "Suspended tenant",
            tenant
        )
        serializer = self.get_serializer(tenant)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=["post"])
    def resume(self, request, pk=None):
        tenant = self.get_object()

        if tenant.subscription_status != "suspended":
            return response.Response(
                {"status": "tenant is not suspended"},
                status=status.HTTP_400_BAD_REQUEST
            )

        tenant.subscription_status = "active"
        tenant.is_active = True
        tenant.save(update_fields=["subscription_status", "is_active", "updated_at"])

        self._create_audit_log(request.user, "Resumed tenant", tenant)
        serializer = self.get_serializer(tenant)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=["post"])
    def extend_subscription(self, request, pk=None):
        """Extiende manualmente la suscripción de un tenant."""
        tenant = self.get_object()
        days = request.data.get("days")
        reason = request.data.get("reason", "").strip()

        if not days or not isinstance(days, int) or days < 1:
            return response.Response(
                {"error": "Se requiere 'days' (entero positivo)."},
                status=status.HTTP_400_BAD_REQUEST
            )

        tenant.extend_subscription(days=days)

        self._create_audit_log(
            request.user,
            f"Extendió suscripción {days} días ({reason})" if reason else f"Extendió suscripción {days} días",
            tenant
        )
        serializer = self.get_serializer(tenant)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=["post"], url_path="change-plan")
    def change_plan(self, request, pk=None):
        """Cambia el plan comercial del tenant y sincroniza suscripciones activas del tenant."""
        tenant = self.get_object()
        plan_id = request.data.get("subscription_plan") or request.data.get("plan_id")

        if plan_id in (None, "", 0, "0"):
            return response.Response(
                {"error": "subscription_plan es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            plan_id = int(plan_id)
        except (TypeError, ValueError):
            return response.Response(
                {"error": "subscription_plan inválido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription, Subscription
        except Exception:
            return response.Response(
                {"error": "No se pudo cargar el módulo de suscripciones."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        try:
            new_plan = SubscriptionPlan.objects.get(id=plan_id)
        except SubscriptionPlan.DoesNotExist:
            return response.Response(
                {"error": "El plan seleccionado no existe."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not getattr(new_plan, "is_active", True):
            return response.Response(
                {"error": "El plan seleccionado no está activo."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        now = timezone.now()
        previous_plan_id = tenant.subscription_plan_id
        previous_plan_name = getattr(getattr(tenant, "subscription_plan", None), "name", None) or tenant.plan_type

        try:
            with transaction.atomic():
                # Aplicar plan y snapshot/límites del tenant (Tenant.save refresca en cambio de plan)
                tenant.subscription_plan = new_plan
                tenant.plan_type = new_plan.name
                tenant.save()

                # Sincronizar UserSubscriptions activas/vigentes de los usuarios del tenant
                user_sub_qs = UserSubscription.objects.select_related("plan", "user").filter(
                    user__tenant=tenant,
                    is_active=True,
                )
                effective_sub = None
                for sub in user_sub_qs:
                    if sub.plan_id != new_plan.id:
                        sub.plan = new_plan
                        sub.save(update_fields=["plan"])
                        try:
                            from apps.subscriptions_api.utils import log_subscription_event
                            log_subscription_event(
                                user=request.user,
                                subscription=sub,
                                action="plan_changed",
                                description=(
                                    f"Plan cambiado administrativamente de "
                                    f"{previous_plan_name or 'N/A'} a {new_plan.name} para tenant {tenant.id}."
                                ),
                            )
                        except Exception:
                            pass
                    # Elegir suscripción efectiva (mayor vigencia)
                    if effective_sub is None:
                        effective_sub = sub
                    else:
                        cur_end = getattr(effective_sub, "end_date", None) or now
                        sub_end = getattr(sub, "end_date", None) or now
                        if sub_end >= cur_end:
                            effective_sub = sub

                # Sincronizar registros Subscription (nivel tenant) activos, si existen
                try:
                    Subscription.objects.filter(tenant=tenant, is_active=True).exclude(plan_id=new_plan.id).update(plan=new_plan)
                except Exception:
                    pass

                # Alinear estado/acceso del tenant con la suscripción efectiva cuando aplique
                tenant_update_fields = []
                if effective_sub and getattr(effective_sub, "is_active", False):
                    end_date = getattr(effective_sub, "end_date", None)
                    if end_date and end_date >= now:
                        if tenant.subscription_status in ("trial", "past_due", "suspended", "cancelled") or tenant.access_until is None:
                            tenant.subscription_status = "active"
                            tenant.is_active = True
                            tenant.trial_end_date = None
                            tenant.access_until = end_date
                            tenant_update_fields.extend(["subscription_status", "is_active", "trial_end_date", "access_until", "updated_at"])
                        elif tenant.access_until != end_date:
                            tenant.access_until = end_date
                            tenant_update_fields.extend(["access_until", "updated_at"])

                if tenant_update_fields:
                    tenant.save(update_fields=list(dict.fromkeys(tenant_update_fields)))

                AuditLog.objects.create(
                    user=request.user,
                    action="UPDATE",
                    description=(
                        f"Cambió plan del tenant {tenant.name} de {previous_plan_name or previous_plan_id} a {new_plan.name}"
                    ),
                    content_type=ContentType.objects.get_for_model(tenant),
                    object_id=tenant.id,
                    ip_address=request.META.get("REMOTE_ADDR"),
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                    source="SYSTEM",
                    extra_data={
                        "previous_plan_id": previous_plan_id,
                        "new_plan_id": new_plan.id,
                        "new_plan_name": new_plan.name,
                        "effective_user_subscription_id": getattr(effective_sub, "id", None),
                    },
                )

        except Exception as e:
            return response.Response(
                {"error": "No se pudo cambiar el plan del tenant.", "detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(tenant)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

    @decorators.action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        tenant = self.get_object()
        current_users = User.objects.filter(tenant=tenant).count()
        current_employees = 0
        try:
            from apps.employees_api.models import Employee
            current_employees = Employee.objects.filter(tenant=tenant).count()
        except Exception:
            current_employees = 0

        return response.Response({
            "max_users": tenant.max_users,
            "max_employees": tenant.max_employees,
            "current_users": current_users,
            "current_employees": current_employees,
        }, status=status.HTTP_200_OK)
    
    @decorators.action(detail=False, methods=["get"])
    def current(self, request):
        """Get current user's tenant"""
        tenant = getattr(request, 'tenant', request.user.tenant)
        if tenant:
            serializer = self.get_serializer(tenant)
            return response.Response(serializer.data)
        return response.Response({"error": "No tenant assigned"}, status=404)
    
    @decorators.action(detail=False, methods=["get"])
    def locale(self, request):
        """Obtener configuración regional del tenant actual"""
        if not request.tenant:
            # Superadmin sin tenant: retornar defaults
            return response.Response({
                "language": "es",
                "timezone": "America/Santo_Domingo",
                "currency": "DOP"
            })
        
        serializer = TenantLocaleSerializer(request.tenant)
        return response.Response(serializer.data)
    
    @decorators.action(detail=False, methods=["get"], url_path="subscription-status")
    def subscription_status(self, request):
        """Check subscription status - will trigger middleware validation"""
        tenant = getattr(request, 'tenant', None)
        if not tenant and hasattr(request, 'user') and getattr(request.user, 'is_authenticated', False):
            tenant = getattr(request.user, 'tenant', None)
        if tenant:
            access_level = tenant.get_access_level()
            payload = {
                "status": tenant.subscription_status,
                "access_level": access_level
            }
            if access_level == 'blocked':
                if tenant.is_paid_access_expired():
                    payload.update({
                        "error": "Subscription expired",
                        "code": "SUBSCRIPTION_EXPIRED",
                        "access_until": tenant.access_until
                    })
                    return response.Response(payload, status=status.HTTP_402_PAYMENT_REQUIRED)
                payload.update({
                    "error": "Subscription required",
                    "code": "SUBSCRIPTION_REQUIRED"
                })
                return response.Response(payload, status=status.HTTP_402_PAYMENT_REQUIRED)
            return response.Response(payload, status=status.HTTP_200_OK)
        return response.Response({"error": "No tenant assigned", "code": "NO_TENANT"}, status=403)
    
    @decorators.action(detail=False, methods=["post"])
    def bulk_activate(self, request):
        """Bulk activate tenants"""
        tenant_ids = request.data.get('tenant_ids', [])
        tenants = Tenant.objects.filter(id__in=tenant_ids, deleted_at__isnull=True)
        tenants.update(is_active=True)
        return response.Response({"activated": len(tenants)})
    
    @decorators.action(detail=False, methods=["post"])
    def bulk_deactivate(self, request):
        """Bulk deactivate tenants"""
        tenant_ids = request.data.get('tenant_ids', [])
        tenants = Tenant.objects.filter(id__in=tenant_ids, deleted_at__isnull=True)
        tenants.update(is_active=False)
        return response.Response({"deactivated": len(tenants)})
    
    @decorators.action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """Bulk soft delete tenants"""
        tenant_ids = request.data.get('tenant_ids', [])
        
        if not tenant_ids:
            return response.Response(
                {"error": "No tenant IDs provided"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if len(tenant_ids) > 20:
            return response.Response(
                {"error": "Maximum 20 tenants per operation"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tenants = Tenant.objects.filter(id__in=tenant_ids, deleted_at__isnull=True)
        deleted_count = 0
        
        for tenant in tenants:
            tenant.soft_delete()
            
            AuditLog.objects.create(
                user=request.user,
                action='BULK_DELETE',
                description=f"Eliminó tenant en bulk: {tenant.name}",
                content_type=ContentType.objects.get_for_model(tenant),
                object_id=tenant.id,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                source='SYSTEM',
                extra_data={
                    'tenant_id': tenant.id,
                    'tenant_name': tenant.name
                }
            )
            deleted_count += 1
        
        return response.Response({"deleted": deleted_count})
