from rest_framework import viewsets, permissions, status, serializers
import logging
logger = logging.getLogger(__name__)
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.utils import timezone
from .models import Sale, CashRegister, CashCount, Promotion, Receipt, PosConfiguration
from .serializers import SaleSerializer, CashRegisterSerializer, CashCountSerializer, PromotionSerializer, ReceiptSerializer, PosConfigurationSerializer
from django.db.models import Sum, Q
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
            
            # Obtener porcentaje de comisión desde configuración o usar valor por defecto
            pos_config = PosConfiguration.objects.filter(user=employee_user).first()
            commission_percentage = pos_config.commission_percentage if pos_config else 50
            
            # Crear ganancia de forma asíncrona
            create_earning_from_sale.delay(
                sale_id=sale.id,
                employee_id=employee.id,
                percentage=commission_percentage
            )
            
        except Employee.DoesNotExist:
            pass

    def create(self, request, *args, **kwargs):
        logger.info(f"Creating sale for user {request.user}")
        logger.debug(f"Sale creation data: {request.data}")
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error creating sale: {str(e)}")
            raise

    def _validate_cash_register(self):
        """Validate if there's an open cash register"""
        open_register = CashRegister.objects.filter(
            user=self.request.user, 
            is_open=True
        ).first()
        
        logger.debug(f"Open register check: {open_register is not None}")
        
        if not open_register:
            logger.warning(f"No open register found for user {self.request.user}")
            raise serializers.ValidationError("Debe abrir una caja antes de realizar ventas")
        return open_register

    def _calculate_sale_total(self, details):
        """Calculate sale total from details"""
        total = Decimal('0')
        for detail in details:
            total += self._validate_and_process_detail(detail)
        return total

    def _validate_and_process_detail(self, detail):
        """Validate and process a single sale detail"""
        try:
            quantity = Decimal(str(detail.get('quantity', 1)))
            if quantity <= 0:
                raise serializers.ValidationError("La cantidad debe ser mayor a 0")
                
            price = Decimal(str(detail.get('price', 0)))
            if price < 0:
                raise serializers.ValidationError("El precio no puede ser negativo")

            if detail.get('content_type') == 'product':
                self._validate_product_stock(detail, quantity)
                
            return quantity * price
            
        except (InvalidOperation, TypeError):
            raise serializers.ValidationError("Valores inválidos para cantidad o precio")
    
    def _get_or_create_active_period(self, employee):
        """Obtiene o crea el período activo para el empleado"""
        from apps.employees_api.earnings_models import FortnightSummary
        from datetime import datetime
        
        # Buscar cualquier período activo (no cerrado) para el empleado
        active_period = FortnightSummary.objects.filter(
            employee=employee,
            closed_at__isnull=True
        ).first()
        
        if active_period:
            return active_period
        
        # No hay período activo, crear uno nuevo para la quincena actual o siguiente
        today = timezone.now().date()
        
        if today.day <= 15:
            start_date = today.replace(day=1)
            end_date = today.replace(day=15)
        else:
            start_date = today.replace(day=16)
            last_day = (today.replace(month=today.month+1, day=1) - timezone.timedelta(days=1)).day
            end_date = today.replace(day=last_day)
        
        year = start_date.year
        month = start_date.month
        fortnight_in_month = 1 if start_date.day <= 15 else 2
        fortnight_number = (month - 1) * 2 + fortnight_in_month
        
        # Verificar si ya existe un período cerrado para esta quincena
        existing_closed = FortnightSummary.objects.filter(
            employee=employee,
            fortnight_year=year,
            fortnight_number=fortnight_number,
            closed_at__isnull=False
        ).exists()
        
        if existing_closed:
            # Si ya hay un período cerrado para esta quincena, crear el siguiente
            if fortnight_number < 24:  # No es la última quincena del año
                fortnight_number += 1
            else:
                # Es la última quincena del año, crear la primera del siguiente año
                year += 1
                fortnight_number = 1
        
        # Usar get_or_create para evitar duplicados
        period, created = FortnightSummary.objects.get_or_create(
            employee=employee,
            fortnight_year=year,
            fortnight_number=fortnight_number,
            defaults={
                'total_earnings': 0,
                'total_services': 0,
                'is_paid': False
            }
        )
        return period

    def perform_create(self, serializer):
        logger.info("Processing sale creation")

        # Validar caja abierta
        open_register = self._validate_cash_register()
        
        # Calcular totales automáticamente
        details = self.request.data.get('details', [])
        total = Decimal('0')
        
        for detail in details:
            try:
                quantity = Decimal(str(detail.get('quantity', 1)))
                if quantity <= 0:
                    raise serializers.ValidationError(f"La cantidad debe ser mayor a 0")
                    
                price = Decimal(str(detail.get('price', 0)))
                if price < 0:
                    raise serializers.ValidationError(f"El precio no puede ser negativo")
                    
                total += quantity * price
                
                # Validar stock si es producto
                if detail.get('content_type') == 'product':
                    from apps.inventory_api.models import Product
                    try:
                        object_id = int(detail.get('object_id'))
                        product = Product.objects.get(id=object_id)
                        if not product.is_active:
                            raise serializers.ValidationError(f"El producto {product.name} no está activo")
                        if product.stock < quantity:
                            raise serializers.ValidationError(
                                f"Stock insuficiente para {product.name}. Disponible: {product.stock}"
                            )
                    except (Product.DoesNotExist, ValueError, TypeError):
                        raise serializers.ValidationError("Producto no encontrado o ID inválido")
            except (InvalidOperation, TypeError):
                raise serializers.ValidationError("Valores inválidos para cantidad o precio")
        
        # Aplicar descuento
        discount = Decimal(str(self.request.data.get('discount', 0)))
        total_with_discount = total - discount
        
        # Determinar el empleado para la venta
        sale_employee = None
        employee_id = self.request.data.get('employee_id')
        if employee_id:
            from apps.employees_api.models import Employee
            try:
                sale_employee = Employee.objects.get(id=employee_id, tenant=self.request.user.tenant)
            except Employee.DoesNotExist:
                pass
        
        # Obtener o crear período activo para el empleado
        active_period = None
        if sale_employee:
            active_period = self._get_or_create_active_period(sale_employee)
        
        # Guardar venta - asignar al empleado que realizó el servicio
        sale = serializer.save(
            user=self.request.user,  # Usuario que registra la venta
            employee=sale_employee,  # Empleado que realizó el servicio
            period=active_period,    # Período activo
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
                if sale_employee:
                    self._create_employee_earning(sale, sale_employee.user)
                    
            except Appointment.DoesNotExist:
                pass
        
        # Si no hay cita pero hay empleado asignado, crear ganancia
        elif sale_employee:
            self._create_employee_earning(sale, sale_employee.user)
       
            

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
        
        # Filtro por teléfono del cliente (protegido contra SQL injection)
        client_phone = self.request.query_params.get('client_phone')
        if client_phone:
            # Validar formato de teléfono para prevenir SQL injection
            import re
            if re.match(r'^[\d\-\+\(\)\s]+$', client_phone):
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
        
        from .serializers import CashRegisterCreateSerializer
        serializer = CashRegisterCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        register = CashRegister.objects.create(
            user=request.user,
            initial_cash=serializer.validated_data['initial_cash']
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
    
    @action(detail=True, methods=['get'])
    def print_receipt(self, request, pk=None):
        """Generar e imprimir recibo"""
        sale = self.get_object()
        
        # Crear o actualizar recibo
        receipt, created = Receipt.objects.get_or_create(
            sale=sale,
            defaults={
                'receipt_number': f"R{sale.id:06d}",
                'template_used': 'default'
            }
        )
        
        # Actualizar contador de impresiones
        receipt.printed_count += 1
        receipt.last_printed = timezone.now()
        receipt.save()
        
        # Generar datos del recibo
        receipt_data = {
            'receipt': ReceiptSerializer(receipt).data,
            'sale': SaleSerializer(sale).data,
            'business_info': {
                'name': 'Barbería App',
                'address': 'Dirección de la barbería',
                'phone': 'Teléfono',
                'email': 'email@barberia.com'
            }
        }
        
        return Response(receipt_data)
    
    @action(detail=False, methods=['get'])
    def search_sales(self, request):
        """Búsqueda avanzada de ventas"""
        queryset = self.get_queryset()
        
        # Filtros
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')
        client_id = request.query_params.get('client_id')
        employee_id = request.query_params.get('employee_id')
        payment_method = request.query_params.get('payment_method')
        
        if date_from:
            try:
                from django.utils.dateparse import parse_date
                parsed_date = parse_date(date_from)
                if parsed_date:
                    queryset = queryset.filter(date_time__date__gte=parsed_date)
            except ValueError:
                pass
        if date_to:
            try:
                from django.utils.dateparse import parse_date
                parsed_date = parse_date(date_to)
                if parsed_date:
                    queryset = queryset.filter(date_time__date__lte=parsed_date)
            except ValueError:
                pass
        if client_id:
            try:
                client_id = int(client_id)
                queryset = queryset.filter(client_id=client_id)
            except (ValueError, TypeError):
                pass
        if employee_id:
            try:
                employee_id = int(employee_id)
                queryset = queryset.filter(employee_id=employee_id)
            except (ValueError, TypeError):
                pass
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)
        
        from apps.utils.response_formatter import StandardResponse
        serializer = self.get_serializer(queryset, many=True)
        return Response(StandardResponse.list_response(
            results=serializer.data,
            count=queryset.count()
        ))

   

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
        
        # Asegurar valores no null
        if register.initial_cash is None:
            register.initial_cash = 0.00
            register.save(update_fields=['initial_cash'])
        if register.final_cash is None:
            register.final_cash = 0.00
            register.save(update_fields=['final_cash'])
            
        return Response(CashRegisterSerializer(register).data)

    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        register = self.get_object()
        if not register.is_open:
            return Response({"detail": "Caja ya está cerrada."}, status=status.HTTP_400_BAD_REQUEST)

        from .serializers import CashRegisterCloseSerializer
        serializer = CashRegisterCloseSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        register.is_open = False
        register.closed_at = timezone.now()
        register.final_cash = serializer.validated_data['final_cash']
        register.save()
        return Response(CashRegisterSerializer(register).data)
    
    @action(detail=True, methods=['post'])
    def cash_count(self, request, pk=None):
        """Arqueo de caja - conteo físico"""
        register = self.get_object()
        counts_data = request.data.get('counts', [])
        
        # Limpiar conteos anteriores
        register.cash_counts.all().delete()
        
        total_counted = Decimal('0')
        for count_data in counts_data:
            count_data['cash_register'] = register.id
            serializer = CashCountSerializer(data=count_data)
            if serializer.is_valid():
                count = serializer.save()
                total_counted += count.total
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        # Calcular diferencia
        expected_cash = register.initial_cash + self._calculate_cash_sales(register)
        difference = total_counted - expected_cash
        
        return Response({
            'total_counted': total_counted,
            'expected_cash': expected_cash,
            'difference': difference,
            'counts': CashCountSerializer(register.cash_counts.all(), many=True).data
        })
    
    def _calculate_cash_sales(self, register):
        """Calcular ventas en efectivo del día del tenant"""
        # Incluir ventas con empleado del tenant y ventas sin empleado del usuario
        cash_sales = Sale.objects.filter(
            Q(employee__tenant=register.user.tenant) | Q(user__tenant=register.user.tenant, employee__isnull=True),
            date_time__date=register.opened_at.date(),
            payment_method='cash'
        ).aggregate(total=Sum('paid'))['total'] or Decimal('0')
        return cash_sales
# Nuevos ViewSets
class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Promotion.objects.filter(is_active=True)
    
    @action(detail=True, methods=['post'])
    def apply_promotion(self, request, pk=None):
        """Aplicar promoción a una venta"""
        promotion = self.get_object()
        cart_total = Decimal(str(request.data.get('cart_total', 0)))
        
        if not promotion.is_active:
            return Response({'error': 'Promoción no activa'}, status=status.HTTP_400_BAD_REQUEST)
        
        if promotion.max_uses and promotion.current_uses >= promotion.max_uses:
            return Response({'error': 'Promoción agotada'}, status=status.HTTP_400_BAD_REQUEST)
        
        if cart_total < promotion.min_amount:
            return Response({'error': f'Monto mínimo requerido: ${promotion.min_amount}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Calcular descuento
        discount = Decimal('0')
        if promotion.type == 'percentage':
            discount = cart_total * (promotion.discount_value / 100)
        elif promotion.type == 'fixed':
            discount = promotion.discount_value
        
        return Response({
            'discount': discount,
            'promotion_name': promotion.name,
            'promotion_id': promotion.id
        })

class PosConfigurationViewSet(viewsets.ModelViewSet):
    queryset = PosConfiguration.objects.all()
    serializer_class = PosConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return PosConfiguration.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
            
@api_view(['GET'])  
def daily_summary(request):
        today = timezone.localdate()
        if request.user.is_superuser:
            sales = Sale.objects.filter(Q(user=request.user) | Q(employee__user=request.user), date_time__date=today)
        elif request.user.tenant:
            sales = Sale.objects.filter(
                Q(employee__tenant=request.user.tenant) | Q(user__tenant=request.user.tenant, employee__isnull=True),
                date_time__date=today
            )
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
def dashboard_stats(request):
    """Estadísticas para el dashboard del POS"""
    from .models import SaleDetail
    from django.db.models import Count
    from datetime import datetime, timedelta
    
    today = timezone.localdate()
    if request.user.is_superuser:
        sales_today = Sale.objects.filter(Q(user=request.user) | Q(employee__user=request.user), date_time__date=today)
        all_sales = Sale.objects.filter(Q(user=request.user) | Q(employee__user=request.user))
    elif request.user.tenant:
        sales_today = Sale.objects.filter(
            Q(employee__tenant=request.user.tenant) | Q(user__tenant=request.user.tenant, employee__isnull=True),
            date_time__date=today
        )
        all_sales = Sale.objects.filter(
            Q(employee__tenant=request.user.tenant) | Q(user__tenant=request.user.tenant, employee__isnull=True)
        )
    else:
        sales_today = Sale.objects.none()
        all_sales = Sale.objects.none()
    
    total_sales = sales_today.aggregate(total=Sum('total'))['total'] or 0
    total_transactions = sales_today.count()
    avg_ticket = total_sales / total_transactions if total_transactions > 0 else 0
    
    # Top productos vendidos hoy
    if request.user.is_superuser:
        product_filter = Q(sale__user=request.user) | Q(sale__employee__user=request.user)
    elif request.user.tenant:
        product_filter = Q(sale__employee__tenant=request.user.tenant) | Q(sale__user__tenant=request.user.tenant, sale__employee__isnull=True)
    else:
        product_filter = Q(pk__isnull=True)  # No results
    
    top_products = SaleDetail.objects.filter(
        product_filter,
        sale__date_time__date=today,
        content_type__model='product'
    ).values('name').annotate(
        sold=Sum('quantity')
    ).order_by('-sold')[:5]
    
    # Ingresos mensuales de los últimos 6 meses
    monthly_revenue = []
    current_date = today.replace(day=1)
    
    for i in range(6):
        month_start = current_date
        if current_date.month == 12:
            month_end = current_date.replace(year=current_date.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            month_end = current_date.replace(month=current_date.month + 1, day=1) - timedelta(days=1)
        
        month_sales = all_sales.filter(
            date_time__gte=month_start,
            date_time__lt=month_end + timedelta(days=1)
        )
        
        month_total = month_sales.aggregate(total=Sum('total'))['total'] or 0
        
        month_names = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
        }
        
        monthly_revenue.insert(0, {
            'month': month_names[current_date.month],
            'revenue': float(month_total)
        })
        
        if current_date.month == 1:
            current_date = current_date.replace(year=current_date.year - 1, month=12)
        else:
            current_date = current_date.replace(month=current_date.month - 1)
    
    return Response({
        'total_sales': float(total_sales),
        'total_transactions': total_transactions,
        'average_ticket': float(avg_ticket),
        'top_products': list(top_products),
        'hourly_data': [],
        'monthly_revenue': monthly_revenue
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
    
    from apps.utils.response_formatter import StandardResponse
    return Response(StandardResponse.list_response(
        results=promotions,
        count=len(promotions)
    ))

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
        
        from apps.utils.response_formatter import StandardResponse
        return Response(StandardResponse.list_response(
            results=categories,
            count=len(categories)
        ))
    except Exception as e:
        # Fallback en caso de error
        categories = [
            {'name': 'Todas', 'value': ''},
            {'name': 'Corte', 'value': 'Corte'},
            {'name': 'Barba', 'value': 'Barba'},
            {'name': 'Productos', 'value': 'Productos'}
        ]
        from apps.utils.response_formatter import StandardResponse
        return Response(StandardResponse.list_response(
            results=categories,
            count=len(categories)
        ))

@api_view(['POST'])
def debug_sale_data(request):
    """Endpoint temporal para debug de datos de venta"""
    print(f"DEBUG ENDPOINT: Datos recibidos: {request.data}")
    print(f"DEBUG ENDPOINT: Usuario: {request.user}")
    print(f"DEBUG ENDPOINT: Headers: {dict(request.headers)}")
    
    return Response({
        'received_data': request.data,
        'user': str(request.user),
        'authenticated': request.user.is_authenticated
    })

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