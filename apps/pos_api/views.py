from rest_framework import viewsets, permissions, status, serializers
import logging
logger = logging.getLogger(__name__)
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from apps.core.tenant_permissions import TenantPermissionByAction
from .models import Sale, CashRegister, CashCount, Promotion, Receipt, PosConfiguration
from .serializers import SaleSerializer, CashRegisterSerializer, CashCountSerializer, PromotionSerializer, ReceiptSerializer, PosConfigurationSerializer
from django.db.models import Sum, Q
from decimal import Decimal, InvalidOperation
from apps.core.permissions import IsSuperAdmin
from apps.settings_api.barbershop_models import BarbershopSettings

class SaleViewSet(viewsets.ModelViewSet):
    queryset = Sale.objects.none()  # Seguro por defecto
    serializer_class = SaleSerializer
    permission_classes = [TenantPermissionByAction]
    
    # Mapeo de permisos por acción
    permission_map = {
        'list': 'pos_api.view_sale',
        'retrieve': 'pos_api.view_sale',
        'create': 'pos_api.add_sale',
        'update': 'pos_api.change_sale',
        'partial_update': 'pos_api.change_sale',
        'destroy': 'pos_api.delete_sale',
        'refund': 'pos_api.refund_sale',
        'open_register': 'pos_api.add_sale',
        'current_register': 'pos_api.view_sale',
        'print_receipt': 'pos_api.view_sale',
        'search_sales': 'pos_api.view_sale',
        'validate_stock': 'pos_api.add_sale',
    }

    def _get_business_info(self, request):
        """
        Unificar datos de negocio para recibos usando BarbershopSettings + PosConfiguration.
        """
        tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
        settings = BarbershopSettings.objects.filter(tenant=tenant).first() if tenant else None

        pos = PosConfiguration.objects.filter(user=request.user).first()
        if not pos and tenant:
            pos = PosConfiguration.objects.filter(user__tenant=tenant).first()

        name = ''
        address = ''
        phone = ''
        email = ''

        if settings:
            name = settings.name or ''
            contact = settings.contact or {}
            address = contact.get('address', '') or ''
            phone = contact.get('phone', '') or ''
            email = contact.get('email', '') or ''

        if pos:
            name = pos.business_name or name
            address = pos.address or address
            phone = pos.phone or phone
            email = pos.email or email

        return {
            'name': name or 'Barberia',
            'address': address or 'Direccion no configurada',
            'phone': phone or 'Telefono no configurado',
            'email': email or ''
        }
    
    def _create_employee_earning(self, sale, employee_user):
        """Crea ganancia automática para el empleado - DEPRECATED"""
        # Esta función ya no es necesaria porque las comisiones se calculan
        # automáticamente desde los snapshots de Sale en PayrollPeriod
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
        from apps.employees_api.earnings_models import PayrollPeriod
        
        # Buscar período abierto o pendiente
        active_period = PayrollPeriod.objects.filter(
            employee=employee,
            status__in=['open', 'pending_approval']
        ).first()
        
        if active_period:
            return active_period
        
        # Crear período para quincena actual
        today = timezone.now().date()
        
        if today.day <= 15:
            start_date = today.replace(day=1)
            end_date = today.replace(day=15)
        else:
            start_date = today.replace(day=16)
            last_day = (today.replace(month=today.month+1 if today.month < 12 else 1, 
                                     year=today.year if today.month < 12 else today.year+1, day=1) 
                       - timezone.timedelta(days=1)).day
            end_date = today.replace(day=last_day)
        
        period = PayrollPeriod.objects.create(
            employee=employee,
            period_type='biweekly',
            period_start=start_date,
            period_end=end_date,
            status='open'
        )
        return period

    def perform_create(self, serializer):
        logger.info("Processing sale creation")

        # Validar caja abierta y obtener la sesión
        open_register = self._validate_cash_register()
        
        # Usar transacción atómica para evitar race conditions
        from django.db import transaction
        
        with transaction.atomic():
            # Calcular totales y validar stock con LOCKS
            details = self.request.data.get('details', [])
            total = Decimal('0')
            
            # Lista para almacenar productos bloqueados
            locked_products = []
            
            for detail in details:
                try:
                    quantity = Decimal(str(detail.get('quantity', 1)))
                    if quantity <= 0:
                        raise serializers.ValidationError(f"La cantidad debe ser mayor a 0")
                        
                    price = Decimal(str(detail.get('price', 0)))
                    if price < 0:
                        raise serializers.ValidationError(f"El precio no puede ser negativo")
                        
                    total += quantity * price
                    
                    # Validar y BLOQUEAR stock si es producto
                    if detail.get('content_type') == 'product':
                        from apps.inventory_api.models import Product
                        try:
                            object_id = int(detail.get('object_id'))
                            # LOCK: Bloquear fila para actualización
                            product = Product.objects.select_for_update().get(id=object_id)
                            
                            if not product.is_active:
                                raise serializers.ValidationError(f"El producto {product.name} no está activo")
                            
                            # Validar stock DESPUÉS del lock
                            if product.stock < quantity:
                                raise serializers.ValidationError(
                                    f"Stock insuficiente para {product.name}. Disponible: {product.stock}, Solicitado: {quantity}"
                                )
                            
                            # CRÍTICO: Actualizar stock DENTRO del lock
                            product.stock -= quantity
                            product.save()
                            
                            locked_products.append((product, quantity))
                        except (Product.DoesNotExist, ValueError, TypeError):
                            raise serializers.ValidationError("Producto no encontrado o ID inválido")
                except (InvalidOperation, TypeError):
                    raise serializers.ValidationError("Valores inválidos para cantidad o precio")
            
            # Aplicar descuento con validación
            discount = Decimal(str(self.request.data.get('discount', 0)))
            
            # CRÍTICO: Validar descuento
            if discount < 0:
                raise serializers.ValidationError("El descuento no puede ser negativo")
            
            if discount > total:
                raise serializers.ValidationError(
                    f"El descuento ({discount}) no puede ser mayor al total ({total})"
                )
            
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
            
            # Guardar venta - asignar sesión de caja Y tenant
            tenant_to_assign = self.request.tenant if hasattr(self.request, 'tenant') else None
            sale = serializer.save(
                user=self.request.user,
                employee=sale_employee,
                period=active_period,
                cash_register=open_register,
                tenant=tenant_to_assign,
                total=total_with_discount
            )
            
            # NUEVO: Recalcular período después de guardar venta
            if active_period:
                active_period.calculate_amounts()
                active_period.save()
            
            # CRÍTICO: Crear movimientos de stock (productos ya actualizados)
            for product, quantity in locked_products:
                from apps.inventory_api.models import StockMovement
                
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
        user = self.request.user
        
        # SuperAdmin: acceso total
        if user.is_superuser:
            qs = Sale.objects.select_related(
                'client', 'employee', 'user', 'user__tenant', 'tenant'
            ).prefetch_related('details', 'details__content_type').all()
        else:
            # Usuario sin tenant: sin acceso
            if not hasattr(self.request, 'tenant') or not self.request.tenant:
                return Sale.objects.none()
            
            # Filtrar por tenant del request
            qs = Sale.objects.select_related(
                'client', 'employee', 'user', 'user__tenant', 'tenant'
            ).prefetch_related('details', 'details__content_type').filter(
                tenant=self.request.tenant
            )
            
            # Si no es staff, solo sus propias ventas
            if not user.is_staff:
                qs = qs.filter(user=user)
        
        # Filtro por teléfono del cliente (protegido contra SQL injection)
        client_phone = self.request.query_params.get('client_phone')
        if client_phone:
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
        from django.db import transaction
        from apps.employees_api.adjustment_models import CommissionAdjustment
        from apps.employees_api.earnings_models import PayrollPeriod
        from django.db import IntegrityError
        import calendar
        
        with transaction.atomic():
            # CRÍTICO: Bloquear venta Y validar tenant
            try:
                if request.user.is_superuser:
                    sale = Sale.objects.select_for_update().get(pk=pk)
                else:
                    # Usuario sin tenant: sin acceso
                    if not hasattr(request, 'tenant') or not request.tenant:
                        return Response(
                            {'error': 'Usuario sin tenant'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    
                    # Filtrar por tenant del request
                    sale = Sale.objects.select_for_update().get(
                        pk=pk,
                        tenant=request.tenant
                    )
            except Sale.DoesNotExist:
                return Response(
                    {'error': 'Venta no encontrada o sin permisos'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if sale.closed:
                return Response(
                    {'error': 'No se puede reembolsar una venta cerrada'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Verificar si ya existe refund (doble protección)
            if hasattr(sale, 'refund'):
                return Response(
                    {'error': 'Esta venta ya fue reembolsada'},
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
            
            # Crear CommissionAdjustment si hay comisión
            if sale.employee and sale.commission_amount_snapshot and sale.commission_amount_snapshot > 0:
                # Validación de tenant (hardening)
                if not request.user.is_superuser:
                    if not hasattr(request, 'tenant') or not request.tenant:
                        return Response(
                            {'error': 'Usuario sin tenant'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                    
                    if sale.employee.tenant_id != request.tenant.id:
                        return Response(
                            {'error': 'No autorizado para reembolsar esta venta'},
                            status=status.HTTP_403_FORBIDDEN
                        )
                
                # Determinar período destino
                target_period = sale.period
                
                # Si período original está finalizado, buscar/crear período abierto
                if target_period and target_period.is_finalized:
                    target_period = PayrollPeriod.objects.filter(
                        employee=sale.employee,
                        status__in=['open', 'pending_approval']
                    ).first()
                    
                    # Si no existe período abierto, crear uno para quincena actual
                    if not target_period:
                        today = timezone.now().date()
                        
                        if today.day <= 15:
                            start_date = today.replace(day=1)
                            end_date = today.replace(day=15)
                        else:
                            start_date = today.replace(day=16)
                            # Usar calendar.monthrange para obtener último día del mes
                            last_day = calendar.monthrange(today.year, today.month)[1]
                            end_date = today.replace(day=last_day)
                        
                        target_period = PayrollPeriod.objects.create(
                            employee=sale.employee,
                            period_type='biweekly',
                            period_start=start_date,
                            period_end=end_date,
                            status='open'
                        )
                
                # Crear adjustment negativo
                if target_period:
                    try:
                        CommissionAdjustment.objects.create(
                            sale=sale,
                            payroll_period=target_period,
                            employee=sale.employee,
                            amount=-sale.commission_amount_snapshot,
                            reason='refund',
                            description=f'Reembolso de venta #{sale.id}',
                            created_by=request.user,
                            tenant=sale.employee.tenant
                        )
                        
                        # Recalcular período afectado (idempotente, no hace save interno)
                        target_period.calculate_amounts()
                        target_period.save()
                        
                    except IntegrityError:
                        # Ya existe adjustment para este refund
                        return Response(
                            {'error': 'Ya existe un ajuste de comisión para este reembolso'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
            
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
            'business_info': self._get_business_info(request)
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

    @action(detail=False, methods=['post'])
    def validate_stock(self, request):
        """Validar stock en tiempo real antes de confirmar venta"""
        from apps.inventory_api.models import Product
        from django.db import transaction
        
        items = request.data.get('items', [])
        errors = []
        
        with transaction.atomic():
            for item in items:
                if item.get('type') == 'product':
                    try:
                        product_id = int(item.get('id'))
                        quantity = int(item.get('quantity', 1))
                        
                        # Bloquear producto para lectura
                        product = Product.objects.select_for_update().get(id=product_id)
                        
                        if product.stock < quantity:
                            errors.append({
                                'product_id': product_id,
                                'product_name': product.name,
                                'requested': quantity,
                                'available': product.stock,
                                'message': f'{product.name}: Stock insuficiente. Disponible: {product.stock}, Solicitado: {quantity}'
                            })
                    except Product.DoesNotExist:
                        errors.append({
                            'product_id': product_id,
                            'message': f'Producto {product_id} no encontrado'
                        })
                    except (ValueError, TypeError):
                        errors.append({
                            'message': 'ID de producto o cantidad inválidos'
                        })
        
        if errors:
            return Response({
                'valid': False,
                'errors': errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response({
            'valid': True,
            'message': 'Stock disponible para todos los productos'
        })

   

class CashRegisterViewSet(viewsets.ModelViewSet):
    queryset = CashRegister.objects.none()  # Seguro por defecto
    serializer_class = CashRegisterSerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'pos_api.view_cashregister',
        'retrieve': 'pos_api.view_cashregister',
        'create': 'pos_api.add_cashregister',
        'update': 'pos_api.change_cashregister',
        'partial_update': 'pos_api.change_cashregister',
        'destroy': 'pos_api.delete_cashregister',
        'current': 'pos_api.view_cashregister',
        'close': 'pos_api.change_cashregister',
        'cash_count': 'pos_api.change_cashregister',
    }
    
    def get_queryset(self):
        user = self.request.user
        
        # SuperAdmin: acceso total
        if user.is_superuser:
            return CashRegister.objects.all()
        
        # Usuario sin tenant: sin acceso
        if not hasattr(self.request, 'tenant') or not self.request.tenant:
            return CashRegister.objects.none()
        
        # Filtrar por tenant del request
        return CashRegister.objects.filter(user__tenant=self.request.tenant)
    
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
        """Calcular ventas en efectivo de ESTA sesión de caja"""
        cash_sales = Sale.objects.filter(
            cash_register=register,
            payment_method='cash'
        ).aggregate(total=Sum('paid'))['total'] or Decimal('0')
        return cash_sales
# Nuevos ViewSets
class PromotionViewSet(viewsets.ModelViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'pos_api.view_promotion',
        'retrieve': 'pos_api.view_promotion',
        'create': 'pos_api.add_promotion',
        'update': 'pos_api.change_promotion',
        'partial_update': 'pos_api.change_promotion',
        'destroy': 'pos_api.delete_promotion',
        'apply_promotion': 'pos_api.view_promotion',
    }
    
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
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'pos_api.view_posconfiguration',
        'retrieve': 'pos_api.view_posconfiguration',
        'create': 'pos_api.add_posconfiguration',
        'update': 'pos_api.change_posconfiguration',
        'partial_update': 'pos_api.change_posconfiguration',
        'destroy': 'pos_api.delete_posconfiguration',
    }
    
    def get_queryset(self):
        return PosConfiguration.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
            
@api_view(['GET'])  
def daily_summary(request):
        today = timezone.localdate()
        
        # Determinar filtro base según usuario
        if request.user.is_superuser:
            base_filter = Q(user=request.user) | Q(employee__user=request.user)
        elif hasattr(request, 'tenant') and request.tenant:
            base_filter = Q(tenant=request.tenant)
        else:
            return Response({
                'date': today,
                'sales_count': 0,
                'total': 0,
                'paid': 0,
                'by_method': [],
                'by_type': {'services': 0, 'products': 0}
            })
        
        # Obtener sesión de caja abierta
        open_register = CashRegister.objects.filter(
            user=request.user,
            is_open=True,
            opened_at__date=today
        ).first()
        
        if open_register:
            # Filtrar ventas de esta sesión de caja
            sales = Sale.objects.filter(cash_register=open_register)
        else:
            # No hay caja abierta, mostrar ventas del día con filtro base
            sales = Sale.objects.filter(base_filter, date_time__date=today)

        total = sales.aggregate(total=Sum('total'))['total'] or 0
        paid = sales.aggregate(paid=Sum('paid'))['paid'] or 0

        by_method = sales.values('payment_method').annotate(total=Sum('paid'))
        
        # Usar agregación SQL para calcular by_type
        from .models import SaleDetail
        from django.db.models import F, Case, When, DecimalField
        
        sale_ids = sales.values_list('id', flat=True)
        by_type_data = SaleDetail.objects.filter(sale_id__in=sale_ids).aggregate(
            products=Sum(
                Case(
                    When(content_type__model='product', then=F('quantity') * F('price')),
                    default=0,
                    output_field=DecimalField()
                )
            ),
            services=Sum(
                Case(
                    When(~Q(content_type__model='product'), then=F('quantity') * F('price')),
                    default=0,
                    output_field=DecimalField()
                )
            )
        )
        
        by_type = {
            'services': float(by_type_data['services'] or 0),
            'products': float(by_type_data['products'] or 0),
        }

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
    from django.core.cache import cache
    from .models import SaleDetail
    from django.db.models import Count, F, Sum, Case, When, DecimalField
    from datetime import datetime, timedelta
    
    # Cache key basado en usuario y tenant
    cache_key = f'dashboard_stats_{request.user.id}_{getattr(request.user.tenant, "id", "none")}'
    cached_data = cache.get(cache_key)
    
    if cached_data:
        return Response(cached_data)
    
    today = timezone.localdate()
    
    # Determinar filtro base según usuario
    if request.user.is_superuser:
        base_filter = Q(user=request.user) | Q(employee__user=request.user)
    elif hasattr(request, 'tenant') and request.tenant:
        base_filter = Q(tenant=request.tenant)
    else:
        base_filter = Q(pk__isnull=True)  # Sin acceso
    
    sales_today = Sale.objects.filter(base_filter, date_time__date=today)
    all_sales = Sale.objects.filter(base_filter)
    
    total_sales = all_sales.aggregate(total=Sum('total'))['total'] or 0
    total_transactions = all_sales.count()
    avg_ticket = total_sales / total_transactions if total_transactions > 0 else 0
    
    # Top productos vendidos hoy usando agregación SQL - OPTIMIZADO
    if request.user.is_superuser:
        product_filter = Q(sale__user=request.user) | Q(sale__employee__user=request.user)
    elif hasattr(request, 'tenant') and request.tenant:
        product_filter = Q(sale__tenant=request.tenant)
    else:
        product_filter = Q(pk__isnull=True)
    
    # ELIMINADO LOOP N+1: Usar agregación SQL directa
    top_products = SaleDetail.objects.filter(
        product_filter,
        sale__date_time__date=today,
        content_type__model='product'
    ).values('name').annotate(
        sold=Sum('quantity')
    ).order_by('-sold')[:5]
    
    # Ingresos mensuales usando agregación SQL - OPTIMIZADO
    monthly_revenue = []
    current_date = today.replace(day=1)
    
    # Usar una sola query para todos los meses
    six_months_ago = current_date - timedelta(days=180)
    monthly_data = all_sales.filter(
        date_time__gte=six_months_ago
    ).extra(
        select={'month': "DATE_TRUNC('month', date_time)"}
    ).values('month').annotate(
        total=Sum('total')
    ).order_by('month')
    
    # Crear diccionario para lookup rápido
    monthly_dict = {item['month'].strftime('%Y-%m'): float(item['total']) for item in monthly_data}
    
    for i in range(6):
        month_start = current_date
        month_key = month_start.strftime('%Y-%m')
        month_total = monthly_dict.get(month_key, 0)
        
        month_names = {
            1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'
        }
        
        monthly_revenue.insert(0, {
            'month': month_names[current_date.month],
            'revenue': month_total
        })
        
        if current_date.month == 1:
            current_date = current_date.replace(year=current_date.year - 1, month=12)
        else:
            current_date = current_date.replace(month=current_date.month - 1)
    
    data = {
        'total_sales': float(total_sales),
        'total_transactions': total_transactions,
        'average_ticket': float(avg_ticket),
        'top_products': list(top_products),
        'hourly_data': [],
        'monthly_revenue': monthly_revenue
    }
    
    # Cache por 60 segundos
    cache.set(cache_key, data, 60)
    
    return Response(data)

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
@permission_classes([IsSuperAdmin])
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
