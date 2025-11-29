from rest_framework import generics, permissions
from rest_framework.response import Response
from django.utils import timezone
from .models import Notification, NotificationTemplate
from .serializers import NotificationSerializer, NotificationTemplateSerializer, NotificationPreferenceSerializer

class NotificationListCreateView(generics.ListCreateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(recipient=user).order_by('-created_at')

class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(recipient=user)

class NotificationTemplateListView(generics.ListAPIView):
    queryset = NotificationTemplate.objects.filter(is_active=True)
    serializer_class = NotificationTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]



class NotificationPreferenceView(generics.RetrieveUpdateAPIView):
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        from .models import NotificationPreference
        obj, created = NotificationPreference.objects.get_or_create(
            user=self.request.user
        )
        return obj

class NotificationStatsView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        from .services import NotificationService
        service = NotificationService()
        stats = service.get_notification_stats(user=request.user)
        return Response(stats)

class SendTestNotificationView(generics.GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        from .services import NotificationService
        from .models import NotificationTemplate
        
        template_id = request.data.get('template_id')
        if not template_id:
            return Response({'error': 'template_id requerido'}, status=400)
        
        try:
            template = NotificationTemplate.objects.get(id=template_id)
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
