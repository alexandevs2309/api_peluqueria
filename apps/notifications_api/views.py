from rest_framework import generics, permissions
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from apps.core.tenant_permissions import tenant_permission
from apps.auth_api.role_utils import get_effective_role_name
from .models import Notification, NotificationTemplate, InAppNotification
from .serializers import NotificationSerializer, NotificationTemplateSerializer, NotificationPreferenceSerializer, InAppNotificationSerializer


def _can_manage_tenant_notifications(user, tenant=None) -> bool:
    role_name = get_effective_role_name(user, tenant=tenant)
    return role_name in {'SuperAdmin', 'Client-Admin'}

class NotificationListCreateView(generics.ListCreateAPIView):
    serializer_class = InAppNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [tenant_permission('notifications_api.add_inappnotification')()]
        return [tenant_permission('notifications_api.view_inappnotification')()]

    def get_queryset(self):
        user = self.request.user
        return InAppNotification.objects.filter(recipient=user).order_by('-created_at')

class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InAppNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH']:
            return [tenant_permission('notifications_api.change_inappnotification')()]
        if self.request.method == 'DELETE':
            return [tenant_permission('notifications_api.delete_inappnotification')()]
        return [tenant_permission('notifications_api.view_inappnotification')()]

    def get_queryset(self):
        user = self.request.user
        return InAppNotification.objects.filter(recipient=user)

class NotificationTemplateListView(generics.ListCreateAPIView):
    serializer_class = NotificationTemplateSerializer
    permission_classes = [tenant_permission('notifications_api.view_notificationtemplate')]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [tenant_permission('notifications_api.add_notificationtemplate')()]
        return [tenant_permission('notifications_api.view_notificationtemplate')()]

    def get_queryset(self):
        tenant = getattr(self.request, 'tenant', getattr(self.request.user, 'tenant', None))
        if not tenant:
            return NotificationTemplate.objects.none()
        # Incluir templates específicos del tenant + templates globales (sin tenant)
        return NotificationTemplate.objects.filter(
            Q(tenant=tenant) | Q(tenant__isnull=True),
            is_active=True
        )

    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', getattr(self.request.user, 'tenant', None))
        serializer.save(tenant=tenant)



class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH']:
            return [tenant_permission('notifications_api.change_notificationpreference')()]
        return [tenant_permission('notifications_api.view_notificationpreference')()]
    
    def get_object(self):
        from .models import NotificationPreference
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj

class NotificationStatsView(generics.GenericAPIView):
    permission_classes = [tenant_permission('notifications_api.view_notification')]
    
    def get(self, request):
        from .services import NotificationService
        service = NotificationService()
        stats = service.get_notification_stats(user=request.user)
        return Response(stats)

class MarkAllReadView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        InAppNotification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'detail': 'Todas las notificaciones marcadas como leídas'})


class SendTestNotificationView(generics.GenericAPIView):
    permission_classes = [tenant_permission('notifications_api.add_notification')]
    
    def post(self, request):
        from .services import NotificationService
        from .models import NotificationTemplate
        
        template_id = request.data.get('template_id')
        if not template_id:
            return Response({'error': 'template_id requerido'}, status=400)
        
        tenant = getattr(self.request, 'tenant', getattr(self.request.user, 'tenant', None))
        
        try:
            template = NotificationTemplate.objects.get(
                Q(id=template_id),
                Q(tenant=tenant) | Q(tenant__isnull=True)
            )
            service = NotificationService()
            
            # Contexto de prueba
            test_context = {
                'user_name': request.user.full_name or request.user.email,
                'test_date': timezone.now().strftime('%d/%m/%Y'),
                'test_time': timezone.now().strftime('%H:%M')
            }
            
            notification = service.create_notification(
                recipient=request.user,
                template=template,
                context_data=test_context
            )
            
            return Response({
                'message': 'Notificación de prueba enviada',
                'notification_id': notification.id
            })
            
        except NotificationTemplate.DoesNotExist:
            return Response({'error': 'Template no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
