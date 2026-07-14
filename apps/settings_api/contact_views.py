from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from apps.emails.service import EmailRenderer
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])  # Público para el landing
def presentation_request(request):
    """Endpoint para solicitudes de presentación (Video Tour) desde el landing"""
    try:
        data = request.data
        
        # Validar solo email (name opcional para landing)
        email = data.get('email')
        if not email:
            return Response({
                'error': 'Campo email es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        name = data.get('name') or 'Lead sin nombre'
        
        # Notificar al equipo de soporte
        try:
            from apps.auth_api.tasks import send_email_async
            support_email = getattr(settings, 'SUPPORT_EMAIL', None)
            if support_email:
                inquiry_html = EmailRenderer.render('presentation_inquiry.html', {
                    'title': 'Nueva solicitud de presentación personalizada',
                    'contact_name': name,
                    'email': email,
                    'phone': data.get('phone', 'No proporcionado'),
                    'business_type': data.get('businessType', 'No especificado'),
                    'demo_message': data.get('message', 'Sin mensaje adicional'),
                })
                send_email_async.delay(
                    subject=f'Nueva solicitud de presentación personalizada - {name}',
                    message=f'Nueva solicitud de presentación de {name} ({email})',
                    from_email='',
                    recipient_list=[support_email] if isinstance(support_email, str) else support_email,
                    html_message=inquiry_html,
                )
        except Exception as e:
            logger.error(f"Error notifying support about presentation request: {str(e)}")
        
        # Acuse al usuario
        try:
            ack_html = EmailRenderer.render('presentation_ack.html', {
                'title': 'Recibimos tu solicitud',
                'contact_name': name if name != 'Lead sin nombre' else '',
            })
            send_email_async.delay(
                subject='Recibimos tu solicitud de presentación - Auron Suite',
                message='Gracias por tu interés en Auron Suite. Hemos recibido tu solicitud de presentación personalizada (Video Tour) de la plataforma.',
                from_email='',
                recipient_list=[email],
                html_message=ack_html,
            )
        except Exception as e:
            logger.error(f"Error sending presentation confirmation to user: {str(e)}")
        
        return Response({
            'message': 'Solicitud de presentación enviada correctamente',
            'status': 'success'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error processing presentation request: {str(e)}")
        return Response({
            'error': 'Error interno del servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([AllowAny])
def newsletter_signup(request):
    """Endpoint para suscripción al newsletter"""
    try:
        email = request.data.get('email')
        
        if not email:
            return Response({
                'error': 'Email es requerido'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Aquí podrías integrar con un servicio como Mailchimp, SendGrid, etc.
        # Por ahora solo logueamos
        logger.info(f"Newsletter signup: {email}")
        
        return Response({
            'message': 'Suscripción al newsletter exitosa',
            'status': 'success'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error processing newsletter signup: {str(e)}")
        return Response({
            'error': 'Error interno del servidor'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)