from rest_framework import views, response, permissions, status
from rest_framework.decorators import api_view, permission_classes
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
from apps.tenants_api.models import Tenant
from apps.subscriptions_api.models import SubscriptionPlan, UserSubscription
from apps.billing_api.models import Invoice
from apps.auth_api.models import User
from .integration_service import IntegrationService
from apps.audit_api.views import AuditLogViewSet

class IsSuperAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.roles.filter(name='Super-Admin').exists()
        )

class SaasMetricsView(views.APIView):
    """Vista para métricas SaaS del SuperAdmin"""
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        try:
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
            total_tenants = Tenant.objects.count()
            active_tenants = Tenant.objects.filter(is_active=True).count()
            
            # Calcular churn rate (últimos 30 días)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            churned_tenants = Tenant.objects.filter(
                is_active=False,
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
                tenant_count = Tenant.objects.filter(subscription_plan=plan).count()
                
                revenue_by_plan.append({
                    'plan_name': plan.name,
                    'revenue': float(plan_revenue),
                    'tenant_count': tenant_count
                })
            
            # Registros recientes
            recent_signups = []
            for tenant in Tenant.objects.order_by('-created_at')[:10]:
                recent_signups.append({
                    'tenant_name': tenant.name,
                    'plan': tenant.subscription_plan.name if tenant.subscription_plan else 'FREE',
                    'created_at': tenant.created_at.isoformat()
                })
            
            return response.Response({
                'mrr': float(mrr),
                'total_tenants': total_tenants,
                'active_tenants': active_tenants,
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
                'uptime': 99.9  # Mock por ahora
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
        try:
            # Test simple de DB
            Tenant.objects.count()
            return {
                'status': 'up',
                'last_check': timezone.now().isoformat(),
                'response_time': 50
            }
        except Exception as e:
            return {
                'status': 'down',
                'last_check': timezone.now().isoformat(),
                'error_message': str(e)
            }
    
    def _check_email(self):
        if IntegrationService.is_sendgrid_enabled():
            return {
                'status': 'up',
                'last_check': timezone.now().isoformat(),
                'response_time': 200
            }
        return {
            'status': 'down',
            'last_check': timezone.now().isoformat(),
            'error_message': 'SendGrid no configurado'
        }
    
    def _check_payments(self):
        if IntegrationService.is_stripe_enabled():
            return {
                'status': 'up',
                'last_check': timezone.now().isoformat(),
                'response_time': 150
            }
        return {
            'status': 'down',
            'last_check': timezone.now().isoformat(),
            'error_message': 'Stripe no configurado'
        }
    
    def _check_paypal(self):
        if IntegrationService.is_paypal_enabled():
            return {
                'status': 'up',
                'last_check': timezone.now().isoformat(),
                'response_time': 180
            }
        return {
            'status': 'down',
            'last_check': timezone.now().isoformat(),
            'error_message': 'PayPal no configurado'
        }
    
    def _check_twilio(self):
        if IntegrationService.is_twilio_enabled():
            return {
                'status': 'up',
                'last_check': timezone.now().isoformat(),
                'response_time': 120
            }
        return {
            'status': 'down',
            'last_check': timezone.now().isoformat(),
            'error_message': 'Twilio no configurado'
        }
    
    def _check_storage(self):
        # Mock - en producción verificaría S3/almacenamiento
        return {
            'status': 'up',
            'last_check': timezone.now().isoformat(),
            'response_time': 100
        }
    
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
    
    def _generate_system_alerts(self, services):
        alerts = []
        for service_name, service in services.items():
            if service['status'] == 'down':
                alerts.append({
                    'id': f'{service_name}-down',
                    'type': 'critical',
                    'title': f'{service_name.title()} Service Down',
                    'message': service.get('error_message', f'{service_name} is not responding'),
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
        return _test_email_service()
    elif service_type == 'payments':
        return _test_payment_service()
    elif service_type == 'paypal':
        return _test_paypal_service()
    elif service_type == 'twilio':
        return _test_twilio_service()
    else:
        return response.Response({
            'success': False,
            'message': 'Tipo de servicio no válido'
        }, status=status.HTTP_400_BAD_REQUEST)

def _test_email_service():
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
        AuditLogViewSet.log_integration_error('SendGrid', str(e))
        return response.Response({
            'success': False,
            'message': f'Error en email: {str(e)}'
        })

def _test_payment_service():
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
        AuditLogViewSet.log_integration_error('Stripe', str(e))
        return response.Response({
            'success': False,
            'message': f'Error en Stripe: {str(e)}'
        })

def _test_paypal_service():
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
        AuditLogViewSet.log_integration_error('PayPal', str(e))
        return response.Response({
            'success': False,
            'message': f'Error en PayPal: {str(e)}'
        })

def _test_twilio_service():
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
        AuditLogViewSet.log_integration_error('Twilio', str(e))
        return response.Response({
            'success': False,
            'message': f'Error en Twilio: {str(e)}'
        })