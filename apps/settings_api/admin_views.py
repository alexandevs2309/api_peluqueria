from rest_framework import views, response, permissions, status
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
import os
import time
from apps.core.permissions import IsSuperAdmin
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription
from apps.billing_api.models import Invoice
from apps.auth_api.models import User
from .integration_service import IntegrationService
from apps.audit_api.views import AuditLogViewSet
from apps.audit_api.models import AuditLog
from django.conf import settings

class SaasMetricsView(views.APIView):
    """Vista para métricas SaaS del SuperAdmin"""
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        try:
            active_tenants_qs = Tenant.objects.filter(
                deleted_at__isnull=True,
                is_active=True
            )
            all_tenants_qs = Tenant.objects.filter(deleted_at__isnull=True)

            # Calcular MRR (Monthly Recurring Revenue)
            current_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = (current_month + timedelta(days=32)).replace(day=1)
            
            monthly_invoices = Invoice.objects.filter(
                issued_at__gte=current_month,
                issued_at__lt=next_month,
                is_paid=True
            )
            mrr = monthly_invoices.aggregate(total=Sum('amount'))['total'] or 0
            
            # Métricas de tenants
            total_tenants = all_tenants_qs.count()
            active_tenants = active_tenants_qs.count()
            today = timezone.localdate()
            trial_tenants = active_tenants_qs.filter(subscription_status='trial').count()
            expiring_trials_7d = active_tenants_qs.filter(
                subscription_status='trial',
                trial_end_date__isnull=False,
                trial_end_date__gte=today,
                trial_end_date__lte=today + timedelta(days=7)
            ).count()

            tenants_with_trial_history = all_tenants_qs.filter(trial_end_date__isnull=False).count()
            converted_trials = all_tenants_qs.filter(
                trial_end_date__isnull=False,
                subscription_status='active'
            ).count()
            trial_conversion_rate = (
                converted_trials / tenants_with_trial_history * 100
            ) if tenants_with_trial_history > 0 else 0
            
            # Calcular churn rate (últimos 30 días)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            churned_tenants = Tenant.objects.filter(
                is_active=False,
                deleted_at__isnull=True,
                updated_at__gte=thirty_days_ago
            ).count()
            churn_rate = (churned_tenants / total_tenants * 100) if total_tenants > 0 else 0
            
            # Growth rate (comparar con mes anterior)
            prev_month = current_month - timedelta(days=1)
            prev_month_start = prev_month.replace(day=1)
            prev_monthly_invoices = Invoice.objects.filter(
                issued_at__gte=prev_month_start,
                issued_at__lt=current_month,
                is_paid=True
            )
            prev_mrr = prev_monthly_invoices.aggregate(total=Sum('amount'))['total'] or 0
            growth_rate = ((mrr - prev_mrr) / prev_mrr * 100) if prev_mrr > 0 else 0
            
            # Revenue por plan
            revenue_by_plan = []
            for plan in SubscriptionPlan.objects.filter(is_active=True):
                plan_invoices = monthly_invoices.filter(subscription__plan=plan)
                plan_revenue = plan_invoices.aggregate(total=Sum('amount'))['total'] or 0
                tenant_count = Tenant.objects.filter(
                    subscription_plan=plan,
                    deleted_at__isnull=True
                ).count()
                
                revenue_by_plan.append({
                    'plan_name': plan.name,
                    'revenue': float(plan_revenue),
                    'tenant_count': tenant_count
                })
            
            # Registros recientes
            recent_signups = []
            for tenant in Tenant.objects.filter(
                deleted_at__isnull=True
            ).order_by('-created_at')[:10]:
                recent_signups.append({
                    'tenant_name': tenant.name,
                    'plan': tenant.subscription_plan.name if tenant.subscription_plan else 'FREE',
                    'created_at': tenant.created_at.isoformat(),
                    'subscription_status': tenant.subscription_status,
                    'trial_days_remaining': tenant.get_trial_days_remaining() if tenant.subscription_status == 'trial' else 0
                })
            
            return response.Response({
                'mrr': float(mrr),
                'total_tenants': total_tenants,
                'active_tenants': active_tenants,
                'trial_tenants': trial_tenants,
                'expiring_trials_7d': expiring_trials_7d,
                'trial_conversion_rate': round(trial_conversion_rate, 2),
                'churn_rate': round(churn_rate, 2),
                'growth_rate': round(growth_rate, 2),
                'revenue_by_plan': revenue_by_plan,
                'recent_signups': recent_signups
            })
            
        except Exception as e:
            return response.Response({
                'error': str(e),
                'message': 'Error al obtener métricas SaaS'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class SystemMonitorView(views.APIView):
    """Vista para monitoreo del sistema"""
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        try:
            # Estado de servicios
            services = {
                'database': self._check_database(),
                'email': self._check_email(),
                'payments': self._check_payments(),
                'paypal': self._check_paypal(),
                'twilio': self._check_twilio(),
                'storage': self._check_storage()
            }
            
            # Calcular estado general
            overall_status = self._calculate_overall_status(services)
            
            # Métricas de rendimiento
            metrics = {
                'response_time': self._calculate_avg_response_time(services),
                'error_rate': self._calculate_error_rate(services),
                'uptime': self._calculate_uptime(services)
            }
            
            # Alertas del sistema
            alerts = self._generate_system_alerts(services)
            
            return response.Response({
                'overall_status': overall_status,
                'services': services,
                'metrics': metrics,
                'alerts': alerts
            })
            
        except Exception as e:
            return response.Response({
                'error': str(e),
                'message': 'Error al obtener estado del sistema'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _check_database(self):
        started = time.perf_counter()
        try:
            Tenant.objects.count()
            return {
                'status': 'up',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'details': 'Consulta ORM completada correctamente'
            }
        except Exception as e:
            return {
                'status': 'down',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'error_message': str(e)
            }
    
    def _check_email(self):
        started = time.perf_counter()
        configured = IntegrationService.is_sendgrid_enabled()
        if configured:
            recent_error = self._get_recent_integration_error('SENDGRID_ERROR')
            if recent_error:
                return {
                    'status': 'degraded',
                    'last_check': timezone.now().isoformat(),
                    'response_time': self._elapsed_ms(started),
                    'details': 'SMTP responde, pero existe un error reciente de entrega/configuración',
                    'error_message': recent_error.description
                }
            return {
                'status': 'up',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'details': 'SMTP/Email configurado y validado'
            }
        return {
            'status': 'down',
            'last_check': timezone.now().isoformat(),
            'response_time': self._elapsed_ms(started),
            'error_message': 'Servicio de email no configurado o invalidado por verificación'
        }
    
    def _check_payments(self):
        started = time.perf_counter()
        if not IntegrationService.is_stripe_enabled():
            return {
                'status': 'down',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'error_message': 'Stripe no configurado'
            }

        stripe_status = self._verify_stripe_connectivity(started)
        if stripe_status:
            return stripe_status

        recent_error = self._get_recent_integration_error('STRIPE_ERROR')
        if recent_error:
            return {
                'status': 'degraded',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'details': 'Stripe configurado, pero con incidencias recientes',
                'error_message': recent_error.description
            }

        return {
            'status': 'degraded',
            'last_check': timezone.now().isoformat(),
            'response_time': self._elapsed_ms(started),
            'details': 'Stripe configurado, pendiente de verificación activa desde el monitor'
        }
    
    def _check_paypal(self):
        started = time.perf_counter()
        if not IntegrationService.is_paypal_enabled():
            return {
                'status': 'down',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'error_message': 'PayPal no configurado'
            }

        paypal_status = self._verify_paypal_connectivity(started)
        if paypal_status:
            return paypal_status

        recent_error = self._get_recent_integration_error('PAYPAL_ERROR')
        if recent_error:
            return {
                'status': 'degraded',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'details': 'PayPal configurado, pero con incidencias recientes',
                'error_message': recent_error.description
            }
        return {
            'status': 'degraded',
            'last_check': timezone.now().isoformat(),
            'response_time': self._elapsed_ms(started),
            'details': 'PayPal configurado, pendiente de verificación activa desde el monitor'
        }
    
    def _check_twilio(self):
        started = time.perf_counter()
        if not IntegrationService.is_twilio_enabled():
            return {
                'status': 'down',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'error_message': 'Twilio no configurado'
            }

        twilio_status = self._verify_twilio_connectivity(started)
        if twilio_status:
            return twilio_status

        recent_error = self._get_recent_integration_error('TWILIO_ERROR')
        if recent_error:
            return {
                'status': 'degraded',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'details': 'Twilio configurado, pero con incidencias recientes',
                'error_message': recent_error.description
            }
        return {
            'status': 'degraded',
            'last_check': timezone.now().isoformat(),
            'response_time': self._elapsed_ms(started),
            'details': 'Twilio configurado, pendiente de verificación activa desde el monitor'
        }
    
    def _check_storage(self):
        started = time.perf_counter()
        media_root = getattr(settings, 'MEDIA_ROOT', None)
        if IntegrationService.is_cloudinary_enabled():
            cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME', '')
            return {
                'status': 'up',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'details': f'Cloudinary configurado para media storage ({cloud_name})'
            }

        if IntegrationService.is_aws_s3_enabled():
            bucket_name = (
                os.getenv('AWS_STORAGE_BUCKET_NAME')
                or getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
            )
            if bucket_name:
                return {
                    'status': 'degraded',
                    'last_check': timezone.now().isoformat(),
                    'response_time': self._elapsed_ms(started),
                    'details': f'S3 configurado sobre bucket {bucket_name}; falta verificación activa de escritura/lectura'
                }
            return {
                'status': 'degraded',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'error_message': 'AWS S3 habilitado, pero falta AWS_STORAGE_BUCKET_NAME'
            }

        if media_root and os.path.isdir(media_root):
            return {
                'status': 'up',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'details': f'Almacenamiento local disponible en {media_root}'
            }

        return {
            'status': 'down',
            'last_check': timezone.now().isoformat(),
            'response_time': self._elapsed_ms(started),
            'error_message': f'No se encontro almacenamiento local disponible en {media_root}'
        }

    def _elapsed_ms(self, started):
        return max(round((time.perf_counter() - started) * 1000, 2), 0.01)

    def _get_recent_integration_error(self, action, hours=24):
        threshold = timezone.now() - timedelta(hours=hours)
        return AuditLog.objects.filter(
            source='INTEGRATIONS',
            action=action,
            timestamp__gte=threshold
        ).order_by('-timestamp').first()

    def _verify_stripe_connectivity(self, started):
        try:
            import stripe
            system_settings = IntegrationService.get_system_settings()
            stripe.api_key = system_settings.stripe_secret_key or os.getenv('STRIPE_SECRET_KEY')
            stripe.Account.retrieve()
            return {
                'status': 'up',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'details': 'Stripe validado mediante consulta a la cuenta'
            }
        except ImportError:
            return {
                'status': 'degraded',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'error_message': 'Stripe está configurado, pero la librería stripe no está instalada en el backend'
            }
        except Exception as e:
            severity = 'down' if self._is_credentials_error(str(e)) else 'degraded'
            return {
                'status': severity,
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'error_message': f'No se pudo validar Stripe en vivo: {str(e)}'
            }

    def _verify_paypal_connectivity(self, started):
        try:
            import requests
            system_settings = IntegrationService.get_system_settings()
            client_id = system_settings.paypal_client_id or os.getenv('PAYPAL_CLIENT_ID')
            client_secret = system_settings.paypal_client_secret or os.getenv('PAYPAL_SECRET')
            sandbox = system_settings.paypal_sandbox
            base_url = 'https://api.sandbox.paypal.com' if sandbox else 'https://api.paypal.com'
            mode = 'sandbox' if sandbox else 'live'

            auth_response = requests.post(
                f'{base_url}/v1/oauth2/token',
                headers={'Accept': 'application/json', 'Accept-Language': 'en_US'},
                data='grant_type=client_credentials',
                auth=(client_id, client_secret),
                timeout=5
            )
            if auth_response.status_code == 200:
                return {
                    'status': 'up',
                    'last_check': timezone.now().isoformat(),
                    'response_time': self._elapsed_ms(started),
                    'details': f'PayPal validado mediante OAuth ({mode})'
                }

            severity = 'down' if auth_response.status_code in (401, 403) else 'degraded'
            return {
                'status': severity,
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'error_message': f'PayPal respondió {auth_response.status_code} durante la validación'
            }
        except Exception as e:
            severity = 'down' if self._is_credentials_error(str(e)) else 'degraded'
            return {
                'status': severity,
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'error_message': f'No se pudo validar PayPal en vivo: {str(e)}'
            }

    def _verify_twilio_connectivity(self, started):
        try:
            from twilio.rest import Client
            system_settings = IntegrationService.get_system_settings()
            account_sid = system_settings.twilio_account_sid or os.getenv('TWILIO_ACCOUNT_SID')
            auth_token = system_settings.twilio_auth_token or os.getenv('TWILIO_AUTH_TOKEN')
            client = Client(account_sid, auth_token)
            client.api.accounts(account_sid).fetch()
            return {
                'status': 'up',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'details': 'Twilio validado mediante lectura de la cuenta'
            }
        except ImportError:
            return {
                'status': 'degraded',
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'error_message': 'Twilio está configurado, pero la librería twilio no está instalada en el backend'
            }
        except Exception as e:
            severity = 'down' if self._is_credentials_error(str(e)) else 'degraded'
            return {
                'status': severity,
                'last_check': timezone.now().isoformat(),
                'response_time': self._elapsed_ms(started),
                'error_message': f'No se pudo validar Twilio en vivo: {str(e)}'
            }

    def _is_credentials_error(self, error_message):
        lowered = str(error_message).lower()
        return any(fragment in lowered for fragment in [
            'invalid',
            'authentication',
            'unauthorized',
            'permission',
            'api key',
            'signature',
            'forbidden',
            'token'
        ])
    
    def _calculate_overall_status(self, services):
        statuses = [s['status'] for s in services.values()]
        if 'down' in statuses:
            return 'critical'
        elif 'degraded' in statuses:
            return 'warning'
        return 'healthy'
    
    def _calculate_avg_response_time(self, services):
        times = [s.get('response_time', 0) for s in services.values() if 'response_time' in s]
        return sum(times) / len(times) if times else 0
    
    def _calculate_error_rate(self, services):
        total = len(services)
        errors = sum(1 for s in services.values() if s['status'] == 'down')
        return (errors / total) * 100

    def _calculate_uptime(self, services):
        total = len(services)
        available = sum(1 for s in services.values() if s['status'] in ('up', 'degraded'))
        return round((available / total) * 100, 2) if total else 0
    
    def _generate_system_alerts(self, services):
        alerts = []
        for service_name, service in services.items():
            if service['status'] == 'down':
                error_message = service.get('error_message', '')
                is_not_configured = isinstance(error_message, str) and 'no configurado' in error_message.lower()
                alert_type = 'info' if settings.DEBUG and is_not_configured else 'critical'
                alert_title = f'{service_name.title()} no configurado' if settings.DEBUG and is_not_configured else f'{service_name.title()} fuera de servicio'
                alerts.append({
                    'id': f'{service_name}-down',
                    'type': alert_type,
                    'title': alert_title,
                    'message': error_message or f'{service_name} no está respondiendo',
                    'created_at': service['last_check'],
                    'resolved': False
                })
        return alerts

@api_view(['POST'])
@permission_classes([IsSuperAdmin])
def test_integration_service(request):
    """Endpoint para probar servicios específicos"""
    service_type = request.data.get('service')
    
    if service_type == 'email':
        return _test_email_service(request)
    elif service_type == 'payments':
        return _test_payment_service(request)
    elif service_type == 'paypal':
        return _test_paypal_service(request)
    elif service_type == 'twilio':
        return _test_twilio_service(request)
    else:
        return response.Response({
            'success': False,
            'message': 'Tipo de servicio no válido'
        }, status=status.HTTP_400_BAD_REQUEST)

def _test_email_service(request):
    try:
        if not IntegrationService.is_sendgrid_enabled():
            return response.Response({
                'success': False,
                'message': 'SendGrid no está configurado'
            })
        
        # Test real de email
        IntegrationService.send_email(
            'test@barbersaas.com',
            'Test Email - BarberSaaS',
            'Email service is working correctly.'
        )
        
        return response.Response({
            'success': True,
            'message': 'Email de prueba enviado correctamente'
        })
    except Exception as e:
        AuditLogViewSet.log_integration_error('SendGrid', str(e), request=request)
        return response.Response({
            'success': False,
            'message': f'Error en email: {str(e)}'
        })

def _test_payment_service(request):
    try:
        if not IntegrationService.is_stripe_enabled():
            return response.Response({
                'success': False,
                'message': 'Stripe no está configurado'
            })
        
        import stripe
        import os
        stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
        
        # Test de conexión
        stripe.Account.retrieve()
        
        return response.Response({
            'success': True,
            'message': 'Stripe configurado correctamente'
        })
    except Exception as e:
        AuditLogViewSet.log_integration_error('Stripe', str(e), request=request)
        return response.Response({
            'success': False,
            'message': f'Error en Stripe: {str(e)}'
        })

def _test_paypal_service(request):
    try:
        if not IntegrationService.is_paypal_enabled():
            return response.Response({
                'success': False,
                'message': 'PayPal no está configurado'
            })
        
        return response.Response({
            'success': True,
            'message': 'PayPal configurado correctamente'
        })
    except Exception as e:
        AuditLogViewSet.log_integration_error('PayPal', str(e), request=request)
        return response.Response({
            'success': False,
            'message': f'Error en PayPal: {str(e)}'
        })

def _test_twilio_service(request):
    try:
        if not IntegrationService.is_twilio_enabled():
            return response.Response({
                'success': False,
                'message': 'Twilio no está configurado'
            })
        
        return response.Response({
            'success': True,
            'message': 'Twilio configurado correctamente'
        })
    except Exception as e:
        AuditLogViewSet.log_integration_error('Twilio', str(e), request=request)
        return response.Response({
            'success': False,
            'message': f'Error en Twilio: {str(e)}'
        })
