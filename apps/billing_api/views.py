from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from .models import Invoice, PaymentAttempt
from .serializers import InvoiceSerializer, PaymentAttemptSerializer
from .permissions import IsOwnerOrAdmin
from rest_framework.response import Response


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated , IsOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return Invoice.objects.all()
        return Invoice.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        # Obtener suscripción activa del usuario
        from apps.subscriptions_api.models import UserSubscription
        active_sub = UserSubscription.objects.filter(user=self.request.user, is_active=True).first()
        serializer.save(user=self.request.user, subscription=active_sub)
    
    @action(detail=True, methods=['post'], url_path='pay')
    def pay(self, request, pk=None):
        invoice = self.get_object()

        if invoice.is_paid:
            return Response(
                {'detail': 'Esta factura ya fue pagada. '},
                status=status.HTTP_400_BAD_REQUEST
            )
        # Simulación del intento de pago (podrías integrar pasarela real después)
        PaymentAttempt.objects.create(invoice=invoice, success=True, message="Pago simulado.")

        invoice.is_paid = True
        invoice.save()
        return Response({'detail': 'Pago exitoso.'}, status=status.HTTP_200_OK)


class PaymentAttemptViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentAttemptSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        if self.request.user.is_superuser:
            return PaymentAttempt.objects.all()
        return PaymentAttempt.objects.filter(invoice__user=self.request.user)
