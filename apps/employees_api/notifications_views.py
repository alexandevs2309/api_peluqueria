from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from datetime import timedelta

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_earnings_notifications(request):
    """Obtiene notificaciones recientes de ganancias para el empleado"""
    from apps.notifications_api.models import Notification
    from .models import Employee
    
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return Response({'notifications': []})
    
    # Obtener notificaciones de los últimos 7 días
    since = timezone.now() - timedelta(days=7)
    
    notifications = Notification.objects.filter(
        recipient=request.user,
        template__notification_type='earnings_available',
        created_at__gte=since
    ).order_by('-created_at')[:10]
    
    data = []
    for notification in notifications:
        data.append({
            'id': notification.id,
            'message': notification.message,
            'amount': notification.metadata.get('amount', '0'),
            'created_at': notification.created_at,
            'status': notification.status
        })
    
    return Response({'notifications': data})

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, notification_id):
    """Marca una notificación como leída"""
    from apps.notifications_api.models import Notification
    
    try:
        notification = Notification.objects.get(
            id=notification_id,
            recipient=request.user
        )
        notification.status = 'sent'  # Marcar como leída
        notification.save()
        
        return Response({'success': True})
    except Notification.DoesNotExist:
        return Response({'error': 'Notificación no encontrada'}, status=404)