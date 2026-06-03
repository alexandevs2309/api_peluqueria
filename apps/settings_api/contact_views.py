from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([AllowAny])  # Público para el landing
def demo_request(request):
    """Endpoint para solicitudes de demo desde el landing"""
    try:
        data = request.data
        
        # Validar campos requeridos
        required_fields = ['name', 'email']
        for field in required_fields:
            if not data.get(field):
                return Response({
                    'error': f'Campo {field} es requerido'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Preparar email
        subject = f'Nueva solicitud de demo - {data.get("name")}'
        message = f"""
        Nueva solicitud de demo recibida:
        
        Nombre: {data.get('name')}
        Email: {data.get('email')}
        Teléfono: {data.get('phone', 'No proporcionado')}
        Tipo de negocio: {data.get('businessType', 'No especificado')}
        
        Mensaje:
        {data.get('message', 'Sin mensaje adicional')}
        """
        
        # Enviar email
        try:
            from apps.auth_api.tasks import send_email_async
            contac_email = getattr(settings, 'CONTACT_EMAIL', None)
            if contac_email:
                send_email_async.delay(
                    subject=subject,
                    message=message,
                    from_email='',
                    recipient_list=[contac_email] if isinstance(contac_email, str) else contac_email,
                )
        except Exception as e:
            logger.error(f"Error sending demo request email: {str(e)}")
        
        return Response({
            'message': 'Solicitud de demo enviada correctamente',
            'status': 'success'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error processing demo request: {str(e)}")
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