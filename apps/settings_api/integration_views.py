from rest_framework import views, response, permissions
from .integration_service import IntegrationService
from apps.audit_api.views import AuditLogViewSet
import os

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
            if integration_type == 'twilio' or integration_type == 'sms':
                if IntegrationService.is_twilio_enabled():
                    # Test SMS
                    IntegrationService.send_sms('+1234567890', 'Test SMS from BarberSaaS')
                    return response.Response({'success': True, 'message': 'SMS de prueba enviado'})
                else:
                    return response.Response({'success': False, 'message': 'Twilio no está habilitado'})
                    
            elif integration_type == 'sendgrid' or integration_type == 'email':
                if not IntegrationService.is_sendgrid_enabled():
                    return response.Response({
                        'success': False, 
                        'message': 'SendGrid no configurado - Verifique SENDGRID_API_KEY en variables de entorno'
                    })
                
                try:
                    # Prueba real de envío
                    IntegrationService.send_email(
                        'test@barbersaas.com', 
                        'Prueba de Configuración - BarberSaaS', 
                        'Si recibes este email, SendGrid está configurado correctamente.'
                    )
                    return response.Response({
                        'success': True, 
                        'message': 'Email de prueba enviado correctamente - Verifique su bandeja de entrada'
                    })
                except Exception as e:
                    AuditLogViewSet.log_integration_error('SendGrid', str(e))
                    return response.Response({
                        'success': False, 
                        'message': f'Error en SendGrid: {str(e)}'
                    })
                    
            elif integration_type == 'stripe' or integration_type == 'payments':
                if not IntegrationService.is_stripe_enabled():
                    return response.Response({
                        'success': False, 
                        'message': 'Stripe no configurado - Verifique STRIPE_SECRET_KEY y STRIPE_PUBLIC_KEY'
                    })
                
                try:
                    # Prueba real de conexión con Stripe
                    import stripe
                    stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
                    
                    # Test de conexión real
                    stripe.Account.retrieve()
                    
                    return response.Response({
                        'success': True, 
                        'message': 'Stripe configurado correctamente - Conexión verificada'
                    })
                except ImportError:
                    return response.Response({
                        'success': False, 
                        'message': 'Stripe library no instalada - pip install stripe'
                    })
                except Exception as e:
                    AuditLogViewSet.log_integration_error('Stripe', str(e))
                    return response.Response({
                        'success': False, 
                        'message': f'Error en Stripe: {str(e)}'
                    })
                    
            elif integration_type == 'paypal':
                if not IntegrationService.is_paypal_enabled():
                    return response.Response({
                        'success': False, 
                        'message': 'PayPal no configurado - Verifique PAYPAL_CLIENT_ID y PAYPAL_SECRET'
                    })
                
                try:
                    # Prueba real de conexión con PayPal
                    import requests
                    
                    client_id = os.getenv('PAYPAL_CLIENT_ID')
                    client_secret = os.getenv('PAYPAL_SECRET')
                    mode = os.getenv('PAYPAL_MODE', 'sandbox')
                    
                    base_url = 'https://api.sandbox.paypal.com' if mode == 'sandbox' else 'https://api.paypal.com'
                    
                    # Test de autenticación
                    auth_response = requests.post(
                        f'{base_url}/v1/oauth2/token',
                        headers={'Accept': 'application/json', 'Accept-Language': 'en_US'},
                        data='grant_type=client_credentials',
                        auth=(client_id, client_secret)
                    )
                    
                    if auth_response.status_code == 200:
                        return response.Response({
                            'success': True, 
                            'message': f'PayPal configurado correctamente - Modo: {mode}'
                        })
                    else:
                        return response.Response({
                            'success': False, 
                            'message': f'Error de autenticación PayPal: {auth_response.status_code}'
                        })
                        
                except Exception as e:
                    AuditLogViewSet.log_integration_error('PayPal', str(e))
                    return response.Response({
                        'success': False, 
                        'message': f'Error en PayPal: {str(e)}'
                    })
                    
            elif integration_type == 'aws_s3':
                if IntegrationService.is_aws_s3_enabled():
                    return response.Response({'success': True, 'message': 'AWS S3 está configurado correctamente'})
                else:
                    return response.Response({'success': False, 'message': 'AWS S3 no está habilitado'})
                    
            else:
                return response.Response({'success': False, 'message': 'Tipo de integración no válido'})
                
        except Exception as e:
            AuditLogViewSet.log_integration_error('System', str(e))
            return response.Response({'success': False, 'message': f'Error: {str(e)}'})