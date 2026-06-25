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
                send_email_async.delay(
                    subject=f'Nueva solicitud de video demo - {name}',
                    message=f"""
                    Nueva solicitud de video demo personalizado:
                    
                    Nombre: {name}
                    Email: {email}
                    Teléfono: {data.get('phone', 'No proporcionado')}
                    Tipo de negocio: {data.get('businessType', 'No especificado')}
                    Mensaje: {data.get('message', 'Sin mensaje adicional')}
                    """,
                    from_email='',
                    recipient_list=[support_email] if isinstance(support_email, str) else support_email,
                )
        except Exception as e:
            logger.error(f"Error notifying support about demo request: {str(e)}")
        
        # Acuse al usuario
        try:
            send_email_async.delay(
                subject='Recibimos tu solicitud de video demo - Auron Suite',
                message=f"""
                Hola{', ' + name if name != 'Lead sin nombre' else ''}
                
                Gracias por tu interés en Auron Suite. Hemos recibido tu solicitud de video demo personalizado.
                
                En las próximas horas uno de nuestros asesores te enviará un video mostrando cómo Auron Suite puede ayudar a tu negocio.
                
                Mientras tanto, puedes visitar nuestra página para más información:
                https://auronsuite.com
                
                Saludos,
                Equipo de Auron Suite
                """,
                from_email='',
                recipient_list=[email],
            )
        except Exception as e:
            logger.error(f"Error sending demo confirmation to user: {str(e)}")
        
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