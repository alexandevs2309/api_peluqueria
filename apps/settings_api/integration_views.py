from rest_framework import views, response, permissions
from .integration_service import IntegrationService

class IntegrationStatusView(views.APIView):
    """Vista para obtener el estado de todas las integraciones"""
    permission_classes = [permissions.IsAdminUser]
    
    def get(self, request):
        """Obtener estado de integraciones disponibles"""
        status = IntegrationService.get_integration_status()
        return response.Response({
            'integrations': status,
            'message': 'Estado de integraciones obtenido correctamente'
        })

class IntegrationTestView(views.APIView):
    """Vista para probar integraciones específicas"""
    permission_classes = [permissions.IsAdminUser]
    
    def post(self, request):
        """Probar una integración específica"""
        integration_type = request.data.get('type')
        
        try:
            if integration_type == 'twilio':
                if IntegrationService.is_twilio_enabled():
                    # Test SMS
                    IntegrationService.send_sms('+1234567890', 'Test SMS from BarberSaaS')
                    return response.Response({'success': True, 'message': 'SMS de prueba enviado'})
                else:
                    return response.Response({'success': False, 'message': 'Twilio no está habilitado'})
                    
            elif integration_type == 'sendgrid':
                if IntegrationService.is_sendgrid_enabled():
                    # Test Email
                    IntegrationService.send_email('test@example.com', 'Test Email', 'Test from BarberSaaS')
                    return response.Response({'success': True, 'message': 'Email de prueba enviado'})
                else:
                    return response.Response({'success': False, 'message': 'SendGrid no está habilitado'})
                    
            elif integration_type == 'stripe':
                if IntegrationService.is_stripe_enabled():
                    return response.Response({'success': True, 'message': 'Stripe está configurado correctamente'})
                else:
                    return response.Response({'success': False, 'message': 'Stripe no está habilitado'})
                    
            elif integration_type == 'aws_s3':
                if IntegrationService.is_aws_s3_enabled():
                    return response.Response({'success': True, 'message': 'AWS S3 está configurado correctamente'})
                else:
                    return response.Response({'success': False, 'message': 'AWS S3 no está habilitado'})
                    
            else:
                return response.Response({'success': False, 'message': 'Tipo de integración no válido'})
                
        except Exception as e:
            return response.Response({'success': False, 'message': f'Error: {str(e)}'})