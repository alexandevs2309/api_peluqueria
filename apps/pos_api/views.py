from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Sale, CashRegister
from .serializers import SaleSerializer, CashRegisterSerializer
from django.db.models import Sum
from decimal import Decimal, InvalidOperation

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        sale = serializer.save(user=self.request.user)
        appointment_id = self.request.data.get('appointment_id')
        if appointment_id:
            from apps.appointments_api.models import Appointment
            try:
                appointment = Appointment.objects.get(id=appointment_id)
                appointment.status = "completed"
                appointment.sale_id = sale.id
                appointment.save()
            except Appointment.DoesNotExist:
                pass
       
            

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            qs = qs.filter(user=self.request.user)
        return qs

   

class CashRegisterViewSet(viewsets.ModelViewSet):
    queryset = CashRegister.objects.all()
    serializer_class = CashRegisterSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        register = self.get_object()
        if not register.is_open:
            return Response({"detail": "Caja ya está cerrada."}, status=status.HTTP_400_BAD_REQUEST)

        final_cash_value = request.data.get('final_cash', 0)
        try:
            final_cash_decimal = Decimal(str(final_cash_value))
        except (InvalidOperation, ValueError):
            return Response(
                {"final_cash": "El valor debe ser un número decimal válido."},
                status=status.HTTP_400_BAD_REQUEST
            )

        register.is_open = False
        register.closed_at = timezone.now()
        register.final_cash = final_cash_decimal
        register.save()
        return Response(CashRegisterSerializer(register).data)
            
@api_view(['GET'])  
def daily_summary(request):
        today = timezone.localdate()
        sales = Sale.objects.filter(user=request.user, date_time__date=today)

        total = sales.aggregate(total=Sum('total'))['total'] or 0
        paid = sales.aggregate(paid=Sum('paid'))['paid'] or 0

        by_method = sales.values('payment_method').annotate(total=Sum('paid'))
        by_type = {
            'services': 0,
            'products': 0,
        }
        for sale in sales:
            for d in sale.details.all():
                if d.content_type == 'product':
                    by_type['products'] += d.quantity * d.price
                else:
                    by_type['services'] += d.quantity * d.price

        return Response({
            'date': today,
            'sales_count': sales.count(),
            'total': total,
            'paid': paid,
            'by_method': list(by_method),
            'by_type': by_type,
        })