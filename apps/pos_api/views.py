from rest_framework import viewsets, permissions, status, serializers
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
        # Validar que hay una caja abierta
        open_register = CashRegister.objects.filter(
            user=self.request.user, 
            is_open=True
        ).first()
        
        if not open_register:
            raise serializers.ValidationError("Debe abrir una caja antes de realizar ventas")
        
        # Calcular totales automáticamente
        details = self.request.data.get('details', [])
        total = Decimal('0')
        
        for detail in details:
            quantity = Decimal(str(detail.get('quantity', 1)))
            price = Decimal(str(detail.get('price', 0)))
            total += quantity * price
            
            # Validar stock si es producto
            if detail.get('content_type') == 'product':
                from apps.inventory_api.models import Product
                try:
                    product = Product.objects.get(id=detail.get('object_id'))
                    if product.stock < quantity:
                        raise serializers.ValidationError(
                            f"Stock insuficiente para {product.name}. Disponible: {product.stock}"
                        )
                except Product.DoesNotExist:
                    raise serializers.ValidationError("Producto no encontrado")
        
        # Aplicar descuento
        discount = Decimal(str(self.request.data.get('discount', 0)))
        total_with_discount = total - discount
        
        sale = serializer.save(
            user=self.request.user,
            total=total_with_discount
        )
        
        # Actualizar inventario
        for detail in details:
            if detail.get('content_type') == 'product':
                from apps.inventory_api.models import Product, StockMovement
                product = Product.objects.get(id=detail.get('object_id'))
                quantity = int(detail.get('quantity', 1))
                
                # Reducir stock
                product.stock -= quantity
                product.save()
                
                # Crear movimiento de stock
                StockMovement.objects.create(
                    product=product,
                    quantity=-quantity,
                    reason=f"Venta #{sale.id}"
                )
        
        # Actualizar cita si existe
        appointment_id = self.request.data.get('appointment_id')
        if appointment_id:
            from apps.appointments_api.models import Appointment
            try:
                appointment = Appointment.objects.get(id=appointment_id)
                appointment.status = "completed"
                appointment.save()
                
                # Actualizar última visita del cliente
                if appointment.client:
                    appointment.client.last_visit = timezone.now()
                    appointment.client.save()
            except Appointment.DoesNotExist:
                pass
       
            

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        # SuperAdmin puede ver todo
        if user.is_superuser:
            return qs
            
        # Filtrar por tenant del usuario
        if user.tenant:
            qs = qs.filter(user__tenant=user.tenant)
        else:
            qs = qs.none()
            
        # Si no es staff, solo sus propias ventas
        if not user.is_staff:
            qs = qs.filter(user=user)
            
        return qs

    @action(detail=False, methods=['post'])
    def open_register(self, request):
        # Verificar que no hay caja abierta
        open_register = CashRegister.objects.filter(
            user=request.user, 
            is_open=True
        ).first()
        
        if open_register:
            return Response(
                {'error': 'Ya tienes una caja abierta'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        initial_cash = Decimal(str(request.data.get('initial_cash', 0)))
        register = CashRegister.objects.create(
            user=request.user,
            initial_cash=initial_cash
        )
        
        return Response(CashRegisterSerializer(register).data)

    @action(detail=False, methods=['get'])
    def current_register(self, request):
        register = CashRegister.objects.filter(
            user=request.user, 
            is_open=True
        ).first()
        
        if not register:
            return Response({'error': 'No hay caja abierta'}, status=status.HTTP_404_NOT_FOUND)
            
        return Response(CashRegisterSerializer(register).data)

    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        sale = self.get_object()
        
        if sale.closed:
            return Response(
                {'error': 'No se puede reembolsar una venta cerrada'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Restaurar inventario
        for detail in sale.details.all():
            if detail.content_type == 'product':
                from apps.inventory_api.models import Product, StockMovement
                try:
                    product = Product.objects.get(id=detail.object_id)
                    product.stock += detail.quantity
                    product.save()
                    
                    StockMovement.objects.create(
                        product=product,
                        quantity=detail.quantity,
                        reason=f"Reembolso venta #{sale.id}"
                    )
                except Product.DoesNotExist:
                    pass
        
        # Marcar como reembolsada
        sale.total = Decimal('0')
        sale.paid = Decimal('0')
        sale.save()
        
        return Response({'detail': 'Venta reembolsada correctamente'})

   

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