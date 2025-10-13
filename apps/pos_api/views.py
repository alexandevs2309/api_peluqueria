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
    
    def _create_employee_earning(self, sale, employee_user):
        """Crea ganancia automática para el empleado"""
        from apps.employees_api.models import Employee
        from apps.employees_api.tasks import create_earning_from_sale
        
        try:
            employee = Employee.objects.get(user=employee_user, tenant=sale.user.tenant)
            
            # Obtener porcentaje de comisión (por defecto 50%)
            commission_percentage = 50
            
            # Crear ganancia de forma asíncrona
            create_earning_from_sale.delay(
                sale_id=sale.id,
                employee_id=employee.id,
                percentage=commission_percentage
            )
            
        except Employee.DoesNotExist:
            pass

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
                appointment.sale = sale  # Vincular venta con cita
                appointment.save()
                
                # Actualizar última visita del cliente
                if appointment.client:
                    appointment.client.last_visit = timezone.now()
                    appointment.client.save()
                    
                # Crear ganancia automática para el empleado
                self._create_employee_earning(sale, appointment.stylist)
                    
            except Appointment.DoesNotExist:
                pass
        
        # Si no hay cita pero hay empleado asignado, crear ganancia
        employee_id = self.request.data.get('employee_id')
        if employee_id and not appointment_id:
            from apps.employees_api.models import Employee
            try:
                employee = Employee.objects.get(id=employee_id, tenant=self.request.user.tenant)
                self._create_employee_earning(sale, employee.user)
            except Employee.DoesNotExist:
                pass
       
            

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        # SuperAdmin puede ver todo
        if user.is_superuser:
            pass  # No filtrar nada
        elif user.tenant:
            # Filtrar por tenant del usuario
            qs = qs.filter(user__tenant=user.tenant)
        else:
            qs = qs.none()
            
        # Si no es staff, solo sus propias ventas
        if not user.is_staff and not user.is_superuser:
            qs = qs.filter(user=user)
        
        # Filtro por teléfono del cliente
        client_phone = self.request.query_params.get('client_phone')
        if client_phone:
            qs = qs.filter(client__phone__icontains=client_phone)
            
        return qs

    @action(detail=False, methods=['post'])
    def open_register(self, request):
        today = timezone.localdate()
        
        # Cerrar cualquier caja abierta anterior (por seguridad)
        CashRegister.objects.filter(
            user=request.user, 
            is_open=True
        ).update(
            is_open=False,
            closed_at=timezone.now(),
            final_cash=0
        )
        
        # Verificar que no hay caja abierta hoy
        open_register = CashRegister.objects.filter(
            user=request.user, 
            is_open=True,
            opened_at__date=today
        ).first()
        
        if open_register:
            return Response(
                {'error': 'Ya tienes una caja abierta hoy'}, 
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
        # Solo buscar cajas abiertas del día actual
        today = timezone.localdate()
        register = CashRegister.objects.filter(
            user=request.user, 
            is_open=True,
            opened_at__date=today
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
    
    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        
        if user.is_superuser:
            return qs
        elif user.tenant:
            return qs.filter(user__tenant=user.tenant)
        else:
            return qs.none()
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Obtener la caja abierta actual del usuario"""
        today = timezone.localdate()
        register = CashRegister.objects.filter(
            user=request.user, 
            is_open=True,
            opened_at__date=today
        ).first()
        
        if not register:
            return Response({'error': 'No hay caja abierta'}, status=status.HTTP_404_NOT_FOUND)
            
        return Response(CashRegisterSerializer(register).data)

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
        if request.user.is_superuser:
            sales = Sale.objects.filter(user=request.user, date_time__date=today)
        elif request.user.tenant:
            sales = Sale.objects.filter(user__tenant=request.user.tenant, date_time__date=today)
        else:
            sales = Sale.objects.none()

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

@api_view(['GET'])
def earnings_my_earnings(request):
    """Ganancias del empleado actual"""
    from datetime import datetime, timedelta
    from django.db.models import Sum
    
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    if request.user.is_superuser:
        sales = Sale.objects.filter(
            user=request.user,
            date_time__date__gte=start_of_month,
            date_time__date__lte=today
        )
    elif request.user.tenant:
        sales = Sale.objects.filter(
            user__tenant=request.user.tenant,
            user=request.user,
            date_time__date__gte=start_of_month,
            date_time__date__lte=today
        )
    else:
        sales = Sale.objects.none()
    
    total_earnings = sales.aggregate(total=Sum('total'))['total'] or 0
    commission_rate = 0.15  # 15% comisión por defecto
    commission = float(total_earnings) * commission_rate
    
    return Response({
        'period': f'{start_of_month} - {today}',
        'total_sales': float(total_earnings),
        'commission_rate': commission_rate,
        'commission': commission,
        'sales_count': sales.count()
    })

@api_view(['GET'])
def earnings_current_fortnight(request):
    """Ganancias de la quincena actual"""
    from datetime import datetime, timedelta
    from django.db.models import Sum
    
    today = timezone.now().date()
    
    if today.day <= 15:
        start_fortnight = today.replace(day=1)
        end_fortnight = today.replace(day=15)
    else:
        start_fortnight = today.replace(day=16)
        if today.month == 12:
            end_fortnight = today.replace(year=today.year+1, month=1, day=1) - timedelta(days=1)
        else:
            end_fortnight = today.replace(month=today.month+1, day=1) - timedelta(days=1)
    
    if request.user.is_superuser:
        sales = Sale.objects.filter(
            user=request.user,
            date_time__date__gte=start_fortnight,
            date_time__date__lte=min(end_fortnight, today)
        )
    elif request.user.tenant:
        sales = Sale.objects.filter(
            user__tenant=request.user.tenant,
            user=request.user,
            date_time__date__gte=start_fortnight,
            date_time__date__lte=min(end_fortnight, today)
        )
    else:
        sales = Sale.objects.none()
    
    total_earnings = sales.aggregate(total=Sum('total'))['total'] or 0
    commission_rate = 0.15
    commission = float(total_earnings) * commission_rate
    
    return Response({
        'period': f'{start_fortnight} - {min(end_fortnight, today)}',
        'total_sales': float(total_earnings),
        'commission_rate': commission_rate,
        'commission': commission,
        'sales_count': sales.count()
    })

@api_view(['GET'])
def dashboard_stats(request):
    """Estadísticas para el dashboard del POS"""
    from .models import SaleDetail
    
    today = timezone.localdate()
    if request.user.is_superuser:
        sales = Sale.objects.filter(user=request.user, date_time__date=today)
    elif request.user.tenant:
        sales = Sale.objects.filter(user__tenant=request.user.tenant, date_time__date=today)
    else:
        sales = Sale.objects.none()
    
    total_sales = sales.aggregate(total=Sum('total'))['total'] or 0
    total_transactions = sales.count()
    avg_ticket = total_sales / total_transactions if total_transactions > 0 else 0
    
    # Top productos vendidos hoy
    from django.db.models import Count
    top_products = SaleDetail.objects.filter(
        sale__user=request.user,
        sale__date_time__date=today,
        content_type__model='product'
    ).values('name').annotate(
        sold=Sum('quantity')
    ).order_by('-sold')[:5]
    
    return Response({
        'total_sales': float(total_sales),
        'total_transactions': total_transactions,
        'average_ticket': float(avg_ticket),
        'top_products': list(top_products),
        'hourly_data': []  # Placeholder para datos por hora
    })

@api_view(['GET'])
def active_promotions(request):
    """Promociones activas - placeholder"""
    promotions = [
        {
            'id': 1,
            'name': '2x1 en Servicios',
            'type': 'buy_x_get_y',
            'conditions': {'buy': 2, 'get': 1, 'category': 'service'},
            'active': True
        },
        {
            'id': 2,
            'name': '10% desc. productos +$50',
            'type': 'percentage',
            'conditions': {'min_amount': 50, 'discount': 0.1},
            'active': True
        }
    ]
    
    return Response({'results': promotions})

@api_view(['GET'])
def pos_categories(request):
    """Categorías para filtros del POS"""
    try:
        from apps.inventory_api.models import Product
        
        # Obtener categorías de productos (Service no tiene category)
        product_categories = list(Product.objects.filter(
            is_active=True,
            category__isnull=False
        ).exclude(category='').values_list('category', flat=True).distinct())
        
        # Categorías base
        categories = [{'name': 'Todas', 'value': ''}]
        
        # Agregar categorías de productos
        for cat in sorted(product_categories):
            categories.append({'name': cat, 'value': cat})
        
        # Agregar categorías estáticas para servicios si no existen
        service_cats = ['Corte', 'Barba', 'Tinte', 'Tratamiento']
        existing_values = [c['value'] for c in categories]
        
        for cat in service_cats:
            if cat not in existing_values:
                categories.append({'name': cat, 'value': cat})
        
        return Response({'results': categories})
    except Exception as e:
        # Fallback en caso de error
        categories = [
            {'name': 'Todas', 'value': ''},
            {'name': 'Corte', 'value': 'Corte'},
            {'name': 'Barba', 'value': 'Barba'},
            {'name': 'Productos', 'value': 'Productos'}
        ]
        return Response({'results': categories})

@api_view(['GET'])
def pos_config(request):
    """Configuración del POS (colores, iconos, denominaciones)"""
    config = {
        'category_colors': {
            'Corte': '#3B82F6',
            'Barba': '#10B981', 
            'Tinte': '#8B5CF6',
            'Tratamiento': '#F59E0B',
            'Manicure': '#EF4444',
            'Pedicure': '#06B6D4',
            'Productos': '#6B7280',
            'default': '#9CA3AF'
        },
        'category_icons': {
            'Corte': 'pi-scissors',
            'Barba': 'pi-user',
            'Tinte': 'pi-palette', 
            'Tratamiento': 'pi-heart',
            'Manicure': 'pi-star',
            'Pedicure': 'pi-circle',
            'Productos': 'pi-shopping-bag',
            'default': 'pi-tag'
        },
        'cash_denominations': [
            {'value': 100, 'count': 0, 'total': 0},
            {'value': 50, 'count': 0, 'total': 0},
            {'value': 20, 'count': 0, 'total': 0},
            {'value': 10, 'count': 0, 'total': 0},
            {'value': 5, 'count': 0, 'total': 0},
            {'value': 1, 'count': 0, 'total': 0},
            {'value': 0.25, 'count': 0, 'total': 0},
            {'value': 0.10, 'count': 0, 'total': 0},
            {'value': 0.05, 'count': 0, 'total': 0},
            {'value': 0.01, 'count': 0, 'total': 0}
        ]
    }
    
    return Response(config)