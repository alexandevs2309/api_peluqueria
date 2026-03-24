from rest_framework import views, response
from .integration_service import IntegrationService
from apps.audit_api.views import AuditLogViewSet
from apps.core.permissions import IsSuperAdmin
import os


class IntegrationStatusView(views.APIView):
    """Vista para obtener el estado de todas las integraciones"""
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        status = IntegrationService.get_integration_status()
        return response.Response({
            'integrations': status,
            'message': 'Estado de integraciones obtenido correctamente'
        })


class IntegrationTestView(views.APIView):
    """Vista para probar integraciones especificas"""
    permission_classes = [IsSuperAdmin]

    def post(self, request):
        integration_type = request.data.get('type')

        try:
            if integration_type in ('twilio', 'sms'):
                if IntegrationService.is_twilio_enabled():
                    IntegrationService.send_sms('+1234567890', 'Test SMS from BarberSaaS')
                    return response.Response({'success': True, 'message': 'SMS de prueba enviado'})
                return response.Response({'success': False, 'message': 'Twilio no esta habilitado'})

            if integration_type in ('sendgrid', 'email'):
                if not IntegrationService.is_sendgrid_enabled():
                    return response.Response({'success': False, 'message': 'Email no configurado'})

                try:
                    system_settings = IntegrationService.get_system_settings()
                    test_recipient = system_settings.support_email or request.user.email
                    IntegrationService.send_email(
                        test_recipient,
                        'Prueba de Configuracion - BarberSaaS',
                        'Si recibes este email, el correo esta configurado correctamente.'
                    )
                    return response.Response({'success': True, 'message': f'Email de prueba enviado a {test_recipient}'})
                except Exception as e:
                    AuditLogViewSet.log_integration_error('SendGrid', str(e), request=request)
                    return response.Response({'success': False, 'message': f'Error en SendGrid: {str(e)}'})

            if integration_type in ('stripe', 'payments'):
                if not IntegrationService.is_stripe_enabled():
                    return response.Response({'success': False, 'message': 'Stripe no configurado'})

                try:
                    import stripe
                    stripe.api_key = IntegrationService.get_system_settings().stripe_secret_key or os.getenv('STRIPE_SECRET_KEY')
                    stripe.Account.retrieve()
                    return response.Response({'success': True, 'message': 'Stripe configurado correctamente'})
                except ImportError:
                    return response.Response({'success': False, 'message': 'Stripe library no instalada - pip install stripe'})
                except Exception as e:
                    AuditLogViewSet.log_integration_error('Stripe', str(e), request=request)
                    return response.Response({'success': False, 'message': f'Error en Stripe: {str(e)}'})

            if integration_type == 'paypal':
                try:
                    import requests
                    system_settings = IntegrationService.get_system_settings()
                    client_id = request.data.get('paypal_client_id') or system_settings.paypal_client_id or os.getenv('PAYPAL_CLIENT_ID')
                    client_secret = request.data.get('paypal_client_secret') or system_settings.paypal_client_secret or os.getenv('PAYPAL_SECRET')
                    sandbox = request.data.get('paypal_sandbox', True)

                    if not client_id or not client_secret:
                        return response.Response({'success': False, 'message': 'Faltan credenciales de PayPal (client_id y client_secret)'})

                    base_url = 'https://api.sandbox.paypal.com' if sandbox else 'https://api.paypal.com'
                    mode = 'sandbox' if sandbox else 'live'
                    auth_response = requests.post(
                        f'{base_url}/v1/oauth2/token',
                        headers={'Accept': 'application/json', 'Accept-Language': 'en_US'},
                        data='grant_type=client_credentials',
                        auth=(client_id, client_secret),
                        timeout=10
                    )

                    if auth_response.status_code == 200:
                        return response.Response({'success': True, 'message': f'PayPal configurado correctamente - Modo: {mode}'})

                    return response.Response({'success': False, 'message': f'Error de autenticacion PayPal: {auth_response.status_code}'})

                except Exception as e:
                    AuditLogViewSet.log_integration_error('PayPal', str(e), request=request)
                    return response.Response({'success': False, 'message': f'Error en PayPal: {str(e)}'})

            if integration_type == 'aws_s3':
                if IntegrationService.is_aws_s3_enabled():
                    return response.Response({'success': True, 'message': 'AWS S3 esta configurado correctamente'})
                return response.Response({'success': False, 'message': 'AWS S3 no esta habilitado'})

            return response.Response({'success': False, 'message': 'Tipo de integracion no valido'})

        except Exception as e:
            AuditLogViewSet.log_integration_error('System', str(e), request=request)
            return response.Response({'success': False, 'message': f'Error: {str(e)}'})
