from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
import json

from .models import Payment, PaymentProvider
from .services import StripeService, OnboardingService, NotificationService
from .serializers import PaymentSerializer
from apps.subscriptions_api.models import SubscriptionPlan

class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Payment.objects.filter(user=self.request.user)
    
    @action(detail=False, methods=['post'])
    def create_subscription_payment(self, request):
        """Crear pago para suscripción"""
        try:
            plan_id = request.data.get('plan_id')
            if not plan_id:
                return Response({'error': 'plan_id is required'}, 
                              status=status.HTTP_400_BAD_REQUEST)
            
            stripe_service = StripeService()
            payment_data = stripe_service.create_subscription_payment(
                request.user, plan_id
            )
            
            return Response(payment_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({'error': str(e)}, 
                          status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def confirm_payment(self, request, pk=None):
        """Confirmar pago y completar onboarding"""
        try:
            payment = self.get_object()
            
            # Actualizar estado del pago
            payment.status = 'completed'
            payment.save()
            
            # Completar onboarding automático
            result = OnboardingService.complete_subscription_purchase(payment.id)
            
            # Enviar notificaciones
            NotificationService.send_payment_confirmation(request.user, payment)
            NotificationService.send_welcome_email(request.user, result['tenant'])
            
            return Response({
                'success': True,
                'tenant_id': result['tenant'].id,
                'subscription_id': result['subscription'].id,
                'message': 'Subscription activated successfully'
            })
            
        except Exception as e:
            return Response({'error': str(e)}, 
                          status=status.HTTP_400_BAD_REQUEST)

from django.views import View

class StripeWebhookView(View):
    """Webhook para recibir eventos de Stripe"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        try:
            payload = request.body
            sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
            
            # Verificar webhook (requiere configuración)
            # event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
            
            # Por ahora, procesar directamente
            event_data = json.loads(payload)
            
            if event_data['type'] == 'payment_intent.succeeded':
                payment_intent = event_data['data']['object']
                
                # Actualizar pago en base de datos
                try:
                    payment = Payment.objects.get(
                        provider_payment_id=payment_intent['id']
                    )
                    payment.status = 'completed'
                    payment.save()
                    
                    # Completar onboarding automáticamente
                    OnboardingService.complete_subscription_purchase(payment.id)
                    
                except Payment.DoesNotExist:
                    pass
            
            return HttpResponse(status=200)
            
        except Exception as e:
            return HttpResponse(status=400)