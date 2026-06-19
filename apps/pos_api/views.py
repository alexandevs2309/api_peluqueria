import stripe
from rest_framework import viewsets, permissions, status, serializers
import logging
logger = logging.getLogger(__name__)
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from django.utils import timezone
from apps.core.tenant_permissions import TenantPermissionByAction
from apps.tenants_api.base_viewsets import TenantScopedViewSet
from .models import Sale, CashRegister, CashCount, Promotion, Receipt, PosConfiguration, NCFSequence, Coupon
from .serializers import SaleSerializer, CashRegisterSerializer, CashCountSerializer, PromotionSerializer, ReceiptSerializer, PosConfigurationSerializer, NCFSequenceSerializer, CouponSerializer, CouponValidationSerializer
from django.db.models import Sum, Q, F
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from apps.core.permissions import IsSuperAdmin
from apps.settings_api.barbershop_models import BarbershopSettings
from django.conf import settings
from apps.audit_api.models import AuditLog
from django.core.exceptions import ValidationError as DjangoValidationError
from apps.subscriptions_api.permissions import HasFeaturePermission

class SaleViewSet(TenantScopedViewSet):
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'cash_register'

    def _get_request_tenant(self):
        return getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
    
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
        'create_payment_intent': 'pos_api.add_sale',
    }

    def _get_business_info(self, request):
        """
        Unificar datos de negocio para recibos usando BarbershopSettings + PosConfiguration.
        """
        tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
        settings = BarbershopSettings.objects.filter(tenant=tenant).first() if tenant else None

        # Buscar config por tenant primero, luego por usuario
        pos = PosConfiguration.objects.filter(tenant=tenant).first()
        if not pos:
            pos = PosConfiguration.objects.filter(user=request.user).first()

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
        logger.info("Creating sale request")
        logger.debug("Sale create payload received")
        try:
            return super().create(request, *args, **kwargs)
        except DjangoValidationError as e:
            logger.error(f"Error creating sale (validation): {str(e)}")
            raise serializers.ValidationError(e.messages if hasattr(e, 'messages') else str(e))
        except Exception as e:
            logger.error(f"Error creating sale: {str(e)}")
            raise

    def _get_request_branch(self):
        branch_id = self.request.data.get('branch_id') or self.request.data.get('branch')
        if not branch_id:
            branch_id = self.request.query_params.get('branch_id') or self.request.query_params.get('branch')

        user = self.request.user
        from apps.auth_api.role_utils import get_effective_role_api
        user_role = get_effective_role_api(user, tenant=getattr(self.request, 'tenant', None))
        is_admin = user_role in ('CLIENT_ADMIN', 'SUPER_ADMIN') or user.is_superuser
        if not is_admin and hasattr(user, 'employee_profile') and user.employee_profile:
            if user.employee_profile.branch_id:
                branch_id = user.employee_profile.branch_id

        return branch_id

    def _validate_cash_register(self):
        tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
        branch_id = self._get_request_branch()

        open_register = CashRegister.objects.filter(
            user=self.request.user,
            tenant=tenant,
            is_open=True
        )
        if branch_id:
            open_register = open_register.filter(branch_id=branch_id)

        open_register = open_register.first()
        
        logger.debug(f"Open register check: {open_register is not None} branch_id={branch_id}")
        
        if not open_register:
            logger.warning(f"No open register found for user {self.request.user} branch_id={branch_id}")
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
        from django.db import IntegrityError
        import calendar
        
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
            last_day = calendar.monthrange(today.year, today.month)[1]
            end_date = today.replace(day=last_day)

        # Si ya existe un período para ese rango (cualquier estado), reutilizarlo
        # para evitar choques de unique_employee_period.
        existing_period = PayrollPeriod.objects.filter(
            employee=employee,
            period_start=start_date,
            period_end=end_date
        ).first()
        if existing_period:
            return existing_period

        try:
            return PayrollPeriod.objects.create(
                employee=employee,
                period_type='biweekly',
                period_start=start_date,
                period_end=end_date,
                status='open'
            )
        except IntegrityError:
            # Carrera de concurrencia: otro request creó el período.
            existing_period = PayrollPeriod.objects.filter(
                employee=employee,
                period_start=start_date,
                period_end=end_date
            ).first()
            if existing_period:
                return existing_period
            raise

    def _get_or_create_adjustment_period(self, employee, reference_date):
        """Obtiene (o crea) un período abierto para aplicar ajustes de comisión."""
        from apps.employees_api.earnings_models import PayrollPeriod
        from django.db import IntegrityError
        import calendar

        # Reusar cualquier período abierto/pending existente
        target_period = PayrollPeriod.objects.filter(
            employee=employee,
            status__in=['open', 'pending_approval']
        ).order_by('period_start').first()
        if target_period and not getattr(target_period, 'is_finalized', False):
            return target_period

        # Si no hay período abierto, buscar/crear el próximo período no finalizado.
        cursor_date = reference_date
        for _ in range(24):  # Límite defensivo: máximo 12 meses (24 quincenas)
            if cursor_date.day <= 15:
                start_date = cursor_date.replace(day=16)
                last_day = calendar.monthrange(cursor_date.year, cursor_date.month)[1]
                end_date = cursor_date.replace(day=last_day)
            else:
                next_month = 1 if cursor_date.month == 12 else cursor_date.month + 1
                next_year = cursor_date.year + 1 if cursor_date.month == 12 else cursor_date.year
                start_date = cursor_date.replace(year=next_year, month=next_month, day=1)
                end_date = cursor_date.replace(year=next_year, month=next_month, day=15)

            existing = PayrollPeriod.objects.filter(
                employee=employee,
                period_start=start_date,
                period_end=end_date
            ).first()
            if existing:
                if existing.status in ['open', 'pending_approval'] and not getattr(existing, 'is_finalized', False):
                    return existing
                cursor_date = existing.period_end
                continue

            try:
                return PayrollPeriod.objects.create(
                    employee=employee,
                    period_type='biweekly',
                    period_start=start_date,
                    period_end=end_date,
                    status='open'
                )
            except IntegrityError:
                existing = PayrollPeriod.objects.filter(
                    employee=employee,
                    period_start=start_date,
                    period_end=end_date
                ).first()
                if existing and existing.status in ['open', 'pending_approval'] and not getattr(existing, 'is_finalized', False):
                    return existing
                if existing:
                    cursor_date = existing.period_end
                    continue
                raise

        raise serializers.ValidationError(
            "No se encontró un período disponible para registrar el ajuste de comisión"
        )

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
                            tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
                            product = Product.objects.select_for_update().get(id=object_id, tenant=tenant)
                            
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

            # Requerir motivo para descuentos altos
            discount_threshold_percent = Decimal(str(getattr(settings, 'POS_HIGH_DISCOUNT_THRESHOLD_PERCENT', 20)))
            if total > 0:
                discount_percent = (discount / total) * Decimal('100')
                if discount_percent > discount_threshold_percent:
                    discount_reason = (self.request.data.get('discount_reason') or '').strip()
                    if len(discount_reason) < 10:
                        raise serializers.ValidationError(
                            f"Descuentos mayores a {discount_threshold_percent}% requieren motivo (mínimo 10 caracteres)"
                        )
            
            # Validar promoción si se especificó promotion_id
            promotion_obj = None
            promotion_id = self.request.data.get('promotion_id')
            if promotion_id:
                try:
                    tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
                    promotion_obj = Promotion.objects.get(id=promotion_id, tenant=tenant)
                    if not promotion_obj.is_active:
                        raise serializers.ValidationError("La promoción no está activa")
                    if promotion_obj.max_uses and promotion_obj.current_uses >= promotion_obj.max_uses:
                        raise serializers.ValidationError("La promoción ha alcanzado su límite de usos")
                    if total < promotion_obj.min_amount:
                        raise serializers.ValidationError(
                            f"Monto mínimo requerido para la promoción: ${promotion_obj.min_amount}"
                        )
                    # Incrementar contador de usos de la promoción
                    promotion_obj.current_uses += 1
                    promotion_obj.save(update_fields=['current_uses'])
                except Promotion.DoesNotExist:
                    raise serializers.ValidationError("Promoción no encontrada")

            # Validar cupón si se especificó coupon_id
            coupon_obj = None
            coupon_id = self.request.data.get('coupon_id')
            if coupon_id:
                try:
                    tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
                    coupon_obj = Coupon.objects.select_for_update().get(id=coupon_id, tenant=tenant)
                    if not coupon_obj.is_active:
                        raise serializers.ValidationError("El cupón no está activo")
                    
                    # Validar vigencia de fechas
                    now = timezone.now()
                    if now < coupon_obj.start_date:
                        raise serializers.ValidationError("El cupón aún no está vigente")
                    if now > coupon_obj.end_date:
                        raise serializers.ValidationError("El cupón ha expirado")

                    # Validar usos
                    if coupon_obj.max_uses is not None and coupon_obj.current_uses >= coupon_obj.max_uses:
                        raise serializers.ValidationError("El cupón ha alcanzado su límite de usos")
                    
                    # Validar monto mínimo
                    if total < coupon_obj.min_purchase_amount:
                        raise serializers.ValidationError(
                            f"Monto mínimo de compra requerido para el cupón: ${coupon_obj.min_purchase_amount}"
                        )
                    
                    # Incrementar usos del cupón
                    coupon_obj.current_uses += 1
                    coupon_obj.save(update_fields=['current_uses'])
                except Coupon.DoesNotExist:
                    raise serializers.ValidationError("Cupón no encontrado")

            total_with_discount = total - discount
            
            # Determinar el empleado para la venta
            sale_employee = None
            employee_id = self.request.data.get('employee_id')
            if employee_id:
                from apps.employees_api.models import Employee
                try:
                    tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
                    if tenant:
                        sale_employee = Employee.objects.get(id=employee_id, tenant=tenant)
                except Employee.DoesNotExist:
                    pass
            
            # Obtener o crear período activo para el empleado
            active_period = None
            if sale_employee:
                active_period = self._get_or_create_active_period(sale_employee)
            
            # Guardar venta - asignar sesión de caja Y tenant Y sucursal
            tenant_to_assign = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
            branch_to_assign = open_register.branch
            if not branch_to_assign and sale_employee:
                branch_to_assign = sale_employee.branch

            sale = serializer.save(
                user=self.request.user,
                employee=sale_employee,
                period=active_period,
                cash_register=open_register,
                tenant=tenant_to_assign,
                branch=branch_to_assign,
                total=total_with_discount,
                promotion=promotion_obj if promotion_id else None,
                coupon=coupon_obj if coupon_id else None
            )

            # --- Generación de NCF (Comprobante Fiscal RD) ---
            ncf_type = self.request.data.get('ncf_type')
            if ncf_type:
                tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
                if tenant:
                    from django.db import transaction
                    # Bloqueo de concurrencia para evitar NCF duplicados
                    with transaction.atomic():
                        sequence = NCFSequence.objects.select_for_update().filter(
                            tenant=tenant,
                            type=ncf_type,
                            is_active=True,
                            current_sequence__lte=F('end_sequence'),
                            expiration_date__gte=timezone.now().date()
                        ).order_by('created_at').first()
                        
                        if not sequence:
                            raise serializers.ValidationError(
                                f"No hay secuencia NCF activa para el tipo {ncf_type}. "
                                "Verifique configuración, rango y fecha de expiración."
                            )
                        
                        ncf = sequence.get_next_ncf()
                        if not ncf:
                            raise serializers.ValidationError(
                                f"Secuencia NCF agotada o vencida para tipo {ncf_type}."
                            )
                        
                        # Asignar NCF y datos fiscales a la venta
                        sale.ncf = ncf
                        sale.ncf_type = ncf_type
                        sale.rnc = self.request.data.get('rnc', '')
                        sale.company_name = self.request.data.get('company_name', '')
                        sale.save(update_fields=['ncf', 'ncf_type', 'rnc', 'company_name'])
                        
                        # Incrementar secuencia
                        sequence.current_sequence += 1
                        sequence.save(update_fields=['current_sequence'])

            # Loyalty: Redimir puntos (descuento por canje)
            from apps.clients_api.models import LoyaltyTransaction
            redeem_points = int(self.request.data.get('redeem_points', 0))
            if redeem_points > 0:
                if not sale.client:
                    raise serializers.ValidationError("Debe seleccionar un cliente para canjear puntos")
                if sale.client.loyalty_points < redeem_points:
                    raise serializers.ValidationError("Puntos insuficientes")
                redeem_rate = Decimal(str(getattr(settings, 'POS_LOYALTY_REDEEM_RATE', 10)))
                discount_from_points = Decimal(str(redeem_points)) / redeem_rate
                discount_from_points = discount_from_points.quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                sale.client.loyalty_points -= redeem_points
                sale.client.save(update_fields=['loyalty_points'])
                LoyaltyTransaction.objects.create(
                    client=sale.client, sale=sale, points=redeem_points,
                    transaction_type='redeemed',
                    description=f'Canje en compra #{sale.id}'
                )
                sale.points_redeemed = redeem_points
                sale.discount += discount_from_points
                sale.total = (sale.total - discount_from_points).quantize(Decimal('0.01'), rounding=ROUND_DOWN)
                if sale.total < Decimal('0'):
                    sale.total = Decimal('0')
                sale.save(update_fields=['points_redeemed', 'discount', 'total'])

            # Loyalty: Auto-earn points on purchase
            if sale.client and sale.total > 0:
                earn_rate = Decimal(str(getattr(settings, 'POS_LOYALTY_EARN_RATE', 100)))
                points_earned = int(sale.total // earn_rate)
                if points_earned > 0:
                    sale.client.loyalty_points += points_earned
                    sale.client.save(update_fields=['loyalty_points'])
                    LoyaltyTransaction.objects.create(
                        client=sale.client, sale=sale, points=points_earned,
                        transaction_type='earned',
                        description=f'Compra #{sale.id}'
                    )
                    sale.points_earned = points_earned
                    sale.save(update_fields=['points_earned'])

            # Auditoría de descuentos altos
            if total > 0:
                discount_percent = (discount / total) * Decimal('100')
                if discount_percent > discount_threshold_percent:
                    AuditLog.objects.create(
                        user=self.request.user,
                        action='ADMIN_ACTION',
                        description=f"Descuento alto aplicado en venta #{sale.id}",
                        content_object=sale,
                        ip_address=self.request.META.get('REMOTE_ADDR'),
                        user_agent=self.request.META.get('HTTP_USER_AGENT', ''),
                        source='SYSTEM',
                        extra_data={
                            'sale_id': sale.id,
                            'discount_amount': str(discount),
                            'discount_percent': str(round(discount_percent, 2)),
                            'discount_reason': (self.request.data.get('discount_reason') or '').strip(),
                        }
                    )
            
            # Recalcular período después de guardar venta.
            # Si el período está finalizado, mover comisión a un ajuste en período abierto.
            if active_period and getattr(active_period, 'is_finalized', False):
                from apps.employees_api.adjustment_models import CommissionAdjustment

                if sale_employee and sale.commission_amount_snapshot and sale.commission_amount_snapshot > 0:
                    target_period = self._get_or_create_adjustment_period(sale_employee, timezone.now().date())

                    CommissionAdjustment.objects.create(
                        sale=sale,
                        payroll_period=target_period,
                        employee=sale_employee,
                        amount=sale.commission_amount_snapshot,
                        reason='correction',
                        description=f'Ajuste automático por venta #{sale.id} en período finalizado',
                        created_by=self.request.user,
                        tenant=sale_employee.tenant
                    )

                    target_period.calculate_amounts()
                    target_period.save()
            elif active_period:
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
                    appointment = Appointment.objects.get(id=appointment_id, tenant=self.request.tenant)
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
        qs = super().get_queryset()
        
        # Enriquecer queryset con select_related y prefetch_related
        qs = qs.select_related(
            'client', 'employee', 'user', 'user__tenant', 'tenant'
        ).prefetch_related('details', 'details__content_type')
        
        # Si no es superusuario ni staff, solo sus propias ventas
        # (Client-Admin ve todas las ventas del tenant)
        if not user.is_superuser and not user.is_staff:
            from apps.auth_api.role_utils import get_effective_role_api
            user_role = get_effective_role_api(user, tenant=getattr(self.request, 'tenant', None))
            if user_role not in ('CLIENT_ADMIN', 'SUPER_ADMIN'):
                qs = qs.filter(user=user)
            
        # Filtro por teléfono del cliente (protegido contra SQL injection)
        client_phone = self.request.query_params.get('client_phone')
        if client_phone:
            import re
            if re.match(r'^[\d\-\+\(\)\s]+$', client_phone):
                qs = qs.filter(client__phone__icontains=client_phone)
            
        return qs

    @action(detail=False, methods=['post'])
    def create_payment_intent(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY

        amount = request.data.get('amount')
        currency = request.data.get('currency', 'usd')

        if not amount or float(amount) <= 0:
            return Response(
                {'error': 'Monto inválido'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            intent = stripe.PaymentIntent.create(
                amount=int(round(float(amount) * 100)),
                currency=currency.lower(),
                metadata={
                    'tenant_id': str(getattr(request, 'tenant_id', '') or ''),
                    'user_id': str(request.user.id),
                    'source': 'pos',
                }
            )
            return Response({'client_secret': intent.client_secret, 'id': intent.id})
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            return Response(
                {'error': 'Error al procesar el pago con tarjeta'},
                status=status.HTTP_502_BAD_GATEWAY
            )

    @action(detail=False, methods=['post'])
    def open_register(self, request):
        today = timezone.localdate()
        tenant = self._get_request_tenant()
        
        branch_id = request.data.get('branch_id') or request.data.get('branch') or request.query_params.get('branch_id') or request.query_params.get('branch')
        user = request.user
        from apps.auth_api.role_utils import get_effective_role_api
        user_role = get_effective_role_api(user, tenant=tenant)
        is_admin = user_role in ('CLIENT_ADMIN', 'SUPER_ADMIN') or user.is_superuser
        if not is_admin and hasattr(user, 'employee_profile') and user.employee_profile:
            if user.employee_profile.branch_id:
                branch_id = user.employee_profile.branch_id

        close_filters = {
            'tenant': tenant,
            'user': request.user, 
            'is_open': True
        }
        if branch_id:
            close_filters['branch_id'] = branch_id
            
        # Cerrar cualquier caja abierta anterior del usuario en esta sucursal (por seguridad)
        CashRegister.objects.filter(**close_filters).update(
            is_open=False,
            closed_at=timezone.now(),
            final_cash=0
        )
        
        open_filters = {
            'tenant': tenant,
            'user': request.user, 
            'is_open': True,
            'opened_at__date': today
        }
        if branch_id:
            open_filters['branch_id'] = branch_id
            
        # Verificar que no hay caja abierta hoy
        open_register = CashRegister.objects.filter(**open_filters).first()
        
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
            tenant=tenant,
            branch_id=branch_id,
            initial_cash=serializer.validated_data['initial_cash']
        )
        
        return Response(CashRegisterSerializer(register).data)

    @action(detail=False, methods=['get'])
    def current_register(self, request):
        tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
        today = timezone.localdate()
        
        branch_id = request.query_params.get('branch_id') or request.query_params.get('branch')
        user = request.user
        from apps.auth_api.role_utils import get_effective_role_api
        user_role = get_effective_role_api(user, tenant=tenant)
        is_admin = user_role in ('CLIENT_ADMIN', 'SUPER_ADMIN') or user.is_superuser
        if not is_admin and hasattr(user, 'employee_profile') and user.employee_profile:
            if user.employee_profile.branch_id:
                branch_id = user.employee_profile.branch_id

        filters = {
            'user': request.user,
            'tenant': tenant,
            'is_open': True,
            'opened_at__date': today
        }
        if branch_id:
            filters['branch_id'] = branch_id

        register = CashRegister.objects.filter(**filters).first()
        
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
        
        reason = (request.data.get('reason') or '').strip()
        if len(reason) < 10:
            return Response(
                {'error': 'El motivo del reembolso es requerido (mínimo 10 caracteres)'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            # CRÍTICO: Bloquear venta Y validar tenant
            try:
                if request.user.is_superuser:
                    tenant = getattr(request, 'tenant', None)
                    if tenant:
                        sale = Sale.objects.select_for_update().get(pk=pk, tenant=tenant)
                    else:
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

            # Regla de negocio: reembolso solo para ventas de productos
            sale_details = list(sale.details.select_related('content_type').all())
            if not sale_details:
                return Response(
                    {'error': 'La venta no tiene detalles para reembolsar'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            has_non_product_items = any(
                getattr(detail.content_type, 'model', None) != 'product'
                for detail in sale_details
            )
            if has_non_product_items:
                return Response(
                    {'error': 'Solo se permiten reembolsos en ventas de productos'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Restaurar inventario
            for detail in sale_details:
                if getattr(detail.content_type, 'model', None) == 'product':
                    from apps.inventory_api.models import Product, StockMovement
                    try:
                        product = Product.objects.get(id=detail.object_id, tenant=self.request.tenant)
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
                            description=f'Reembolso de venta #{sale.id}. Motivo: {reason}',
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
            
            # Marcar como reembolsada respetando inmutabilidad financiera.
            # El modelo Sale permite transición de estado confirmed -> refunded.
            refunded_amount = sale.total
            sale.status = 'refunded'
            sale.closed = True
            sale.save(update_fields=['status', 'closed', 'updated_at'])

            AuditLog.objects.create(
                user=request.user,
                action='ADMIN_ACTION',
                description=f"Reembolso procesado para venta #{sale.id}",
                content_object=sale,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                source='SYSTEM',
                extra_data={
                    'sale_id': sale.id,
                    'refund_reason': reason,
                    'refund_amount': str(refunded_amount),
                }
            )
            
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
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
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
                        product = Product.objects.select_for_update().get(id=product_id, tenant=self.request.tenant)
                        
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

   

class NCFSequenceViewSet(TenantScopedViewSet):
    queryset = NCFSequence.objects.all()
    serializer_class = NCFSequenceSerializer
    permission_classes = [TenantPermissionByAction]
    permission_map = {
        'list': 'pos_api.view_ncfsequence',
        'retrieve': 'pos_api.view_ncfsequence',
        'create': 'pos_api.add_ncfsequence',
        'update': 'pos_api.change_ncfsequence',
        'partial_update': 'pos_api.change_ncfsequence',
        'destroy': 'pos_api.delete_ncfsequence',
    }

class CashRegisterViewSet(TenantScopedViewSet):
    queryset = CashRegister.objects.all()
    serializer_class = CashRegisterSerializer
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'cash_register'
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

    def _get_request_tenant(self):
        return getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        is_open = self.request.query_params.get('is_open')
        if is_open is not None:
            is_open_bool = is_open.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_open=is_open_bool)
            
        user_id = self.request.query_params.get('user') or self.request.query_params.get('user_id')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Anotar sales_amount para evitar N+1 en serialización
        from django.db.models import Sum, OuterRef, Subquery
        from django.db.models.functions import Coalesce
        from decimal import Decimal
        from .models import Payment
        payment_subquery = Payment.objects.filter(
            sale__cash_register=OuterRef('pk'),
            sale__tenant=OuterRef('tenant'),
            method='cash',
            sale__status='confirmed'
        ).values('sale__cash_register').annotate(
            total=Sum('amount')
        ).values('total')
        queryset = queryset.annotate(
            _sales_amount_annotated=Coalesce(Subquery(payment_subquery), Decimal('0.00'))
        )
        
        return queryset
            
        return queryset
    
    def perform_create(self, serializer):
        tenant = self._get_request_tenant()
        
        branch_id = self.request.data.get('branch_id') or self.request.data.get('branch') or self.request.query_params.get('branch_id') or self.request.query_params.get('branch')
        user = self.request.user
        from apps.auth_api.role_utils import get_effective_role_api
        user_role = get_effective_role_api(user, tenant=tenant)
        is_admin = user_role in ('CLIENT_ADMIN', 'SUPER_ADMIN') or user.is_superuser
        if not is_admin and hasattr(user, 'employee_profile') and user.employee_profile:
            if user.employee_profile.branch_id:
                branch_id = user.employee_profile.branch_id
                
        serializer.save(user=self.request.user, tenant=tenant, branch_id=branch_id)

    @action(detail=False, methods=['get'])
    def current(self, request):
        """Obtener la caja abierta actual del usuario"""
        tenant = self._get_request_tenant()
        
        branch_id = request.query_params.get('branch_id') or request.query_params.get('branch')
        user = request.user
        from apps.auth_api.role_utils import get_effective_role_api
        user_role = get_effective_role_api(user, tenant=tenant)
        is_admin = user_role in ('CLIENT_ADMIN', 'SUPER_ADMIN') or user.is_superuser
        if not is_admin and hasattr(user, 'employee_profile') and user.employee_profile:
            if user.employee_profile.branch_id:
                branch_id = user.employee_profile.branch_id

        filters = {
            'tenant': tenant,
            'user': request.user,
            'is_open': True
        }
        if branch_id:
            filters['branch_id'] = branch_id

        register = CashRegister.objects.filter(**filters).first()
        
        if not register:
            return Response({'register': None, 'is_open': False})
        
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
class PromotionViewSet(TenantScopedViewSet):
    queryset = Promotion.objects.all()
    serializer_class = PromotionSerializer
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'cash_register'
    permission_map = {
        'list': 'pos_api.view_promotion',
        'retrieve': 'pos_api.view_promotion',
        'create': 'pos_api.add_promotion',
        'update': 'pos_api.change_promotion',
        'partial_update': 'pos_api.change_promotion',
        'destroy': 'pos_api.delete_promotion',
        'apply_promotion': 'pos_api.view_promotion',
    }
    
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
        
        # Validar tipo de promoción soportado
        if promotion.type not in ('percentage', 'fixed'):
            return Response({
                'error': f'Tipo de promoción "{promotion.get_type_display()}" no implementado'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Calcular descuento
        discount = Decimal('0')
        if promotion.type == 'percentage':
            discount = cart_total * (promotion.discount_value / 100)
        elif promotion.type == 'fixed':
            discount = promotion.discount_value

        # NOTA: current_uses se incrementa en perform_create de SaleViewSet,
        # no aquí, para evitar conteo doble o incremento en previews sin venta real.

        return Response({
            'discount': discount,
            'promotion_name': promotion.name,
            'promotion_id': promotion.id
        })

class CouponViewSet(TenantScopedViewSet):
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'cash_register'
    permission_map = {
        'list': 'pos_api.view_coupon',
        'retrieve': 'pos_api.view_coupon',
        'create': 'pos_api.add_coupon',
        'update': 'pos_api.change_coupon',
        'partial_update': 'pos_api.change_coupon',
        'destroy': 'pos_api.delete_coupon',
        'validate': 'pos_api.view_coupon',
    }

    @action(detail=False, methods=['post'])
    def validate(self, request):
        """Valida un código de cupón para el carrito actual"""
        serializer = CouponValidationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        code = serializer.validated_data['code']
        cart_total = serializer.validated_data['cart_total']
        
        tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({'error': 'No tenant context found'}, status=status.HTTP_400_BAD_REQUEST)

        # Buscar cupón por código y tenant
        try:
            coupon = Coupon.objects.get(code=code, tenant=tenant)
        except Coupon.DoesNotExist:
            return Response({'error': 'El cupón ingresado no existe.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Validar si está activo
        if not coupon.is_active:
            return Response({'error': 'El cupón no está activo.'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validar vigencia de fechas
        now = timezone.now()
        if now < coupon.start_date:
            return Response({'error': 'El cupón aún no ha comenzado su periodo de vigencia.'}, status=status.HTTP_400_BAD_REQUEST)
        if now > coupon.end_date:
            return Response({'error': 'El cupón ha expirado.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Validar límites de usos
        if coupon.max_uses is not None and coupon.current_uses >= coupon.max_uses:
            return Response({'error': 'El cupón ha superado el límite máximo de usos permitidos.'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Validar monto mínimo de compra
        if cart_total < coupon.min_purchase_amount:
            return Response({'error': f'Compra mínima requerida para este cupón: ${coupon.min_purchase_amount:.2f}'}, status=status.HTTP_400_BAD_REQUEST)
            
        # Calcular el descuento aplicable
        discount = Decimal('0.00')
        if coupon.type == 'percentage':
            discount = cart_total * (coupon.value / Decimal('100.00'))
        elif coupon.type == 'fixed':
            discount = coupon.value
            
        # Asegurarse de que el descuento no supere el total del carrito
        if discount > cart_total:
            discount = cart_total
            
        return Response({
            'coupon_id': coupon.id,
            'code': coupon.code,
            'type': coupon.type,
            'value': coupon.value,
            'discount': discount
        })

class PosConfigurationViewSet(TenantScopedViewSet):
    queryset = PosConfiguration.objects.all()
    serializer_class = PosConfigurationSerializer
    permission_classes = [TenantPermissionByAction, HasFeaturePermission]
    required_feature = 'cash_register'
    permission_map = {
        'list': 'pos_api.view_posconfiguration',
        'retrieve': 'pos_api.view_posconfiguration',
        'create': 'pos_api.add_posconfiguration',
        'update': 'pos_api.change_posconfiguration',
        'partial_update': 'pos_api.change_posconfiguration',
        'destroy': 'pos_api.delete_posconfiguration',
    }
    
    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            tenant = getattr(self.request, 'tenant', None)
            if tenant:
                return PosConfiguration.objects.filter(
                    Q(tenant=tenant) | Q(tenant__isnull=True, user__tenant=tenant)
                )
            return PosConfiguration.objects.all()
        tenant = getattr(self.request, 'tenant', None) or getattr(user, 'tenant', None)
        if not tenant:
            return PosConfiguration.objects.none()
        # Usar el FK directo tenant si está presente, o fallback a user__tenant
        return PosConfiguration.objects.filter(
            Q(tenant=tenant) | Q(tenant__isnull=True, user__tenant=tenant)
        )
    
    def perform_create(self, serializer):
        tenant = getattr(self.request, 'tenant', None) or getattr(self.request.user, 'tenant', None)
        serializer.save(user=self.request.user, tenant=tenant)
            
@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def daily_summary(request):
        today = timezone.localdate()
        
        # Determinar filtro base según usuario
        tenant = getattr(request, 'tenant', None)
        if request.user.is_superuser:
            if tenant:
                base_filter = Q(tenant=tenant)
            else:
                base_filter = Q()
        elif tenant:
            base_filter = Q(tenant=tenant)
        else:
            return Response({
                'date': today,
                'sales_count': 0,
                'total': 0,
                'paid': 0,
                'by_method': [],
                'by_type': {'services': 0, 'products': 0}
            })
        
        branch_id = request.GET.get('branch_id') or request.GET.get('branch')
        if branch_id:
            base_filter = base_filter & Q(branch_id=branch_id)
        
        # Obtener sesión de caja abierta
        open_register = None
        if tenant:
            from apps.auth_api.role_utils import get_effective_role_api
            user_role = get_effective_role_api(request.user, tenant=tenant)
            if request.user.is_superuser or user_role == 'CLIENT_ADMIN':
                open_register = CashRegister.objects.filter(
                    tenant=tenant,
                    is_open=True
                ).first()
            else:
                open_register = CashRegister.objects.filter(
                    user=request.user,
                    tenant=tenant,
                    is_open=True
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
@permission_classes([permissions.IsAuthenticated])
def dashboard_stats(request):
    """Estadísticas para el dashboard del POS con filtros avanzados"""
    from django.core.cache import cache
    from .models import SaleDetail
    from django.db.models import Count, Sum
    from datetime import datetime, timedelta

    today = timezone.localdate()

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    branch_id = request.GET.get('branch_id') or request.GET.get('branch')

    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            start_date = today.replace(day=1)
    else:
        start_date = today.replace(day=1)

    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
    else:
        end_date = today

    tenant = getattr(request, 'tenant', None)
    tenant_id = getattr(tenant, 'id', None) or getattr(request.user.tenant, 'id', 'none')
    cache_key = f'dashboard_stats_{request.user.id}_{tenant_id}_{start_date}_{end_date}_{branch_id or "all"}'
    cached_data = cache.get(cache_key)
    if cached_data:
        return Response(cached_data)

    base_filter = Q(pk__isnull=True)
    if request.user.is_superuser:
        if tenant:
            base_filter = Q(tenant=tenant)
        else:
            base_filter = Q()
    elif tenant:
        base_filter = Q(tenant=tenant)

    if branch_id:
        base_filter = base_filter & Q(branch_id=branch_id)

    range_filter = base_filter & Q(date_time__date__gte=start_date) & Q(date_time__date__lte=end_date)
    today_filter = base_filter & Q(date_time__date=today)

    all_in_range = Sale.objects.filter(range_filter)
    sales_today = Sale.objects.filter(today_filter)

    # KPIs del rango
    revenue_range = all_in_range.aggregate(total=Sum('total'))['total'] or 0
    transactions_range = all_in_range.count()
    avg_ticket = revenue_range / transactions_range if transactions_range > 0 else 0
    revenue_today = sales_today.aggregate(total=Sum('total'))['total'] or 0

    # Método de pago breakdown
    payment_breakdown = all_in_range.values('payment_method').annotate(
        total=Sum('total'), count=Count('id')
    ).order_by('-total')

    # Top productos
    top_products = SaleDetail.objects.filter(
        Q(sale__in=all_in_range), content_type__model='product'
    ).values('name').annotate(sold=Sum('quantity')).order_by('-sold')[:5]

    # Top servicios
    top_services = SaleDetail.objects.filter(
        Q(sale__in=all_in_range), content_type__model='service'
    ).values('name').annotate(
        sold=Sum('quantity'), revenue=Sum('price')
    ).order_by('-revenue')[:5]

    user_sales_today = Sale.objects.filter(today_filter & Q(user=request.user))
    user_sales_count = user_sales_today.count()
    user_sales_revenue = user_sales_today.aggregate(total=Sum('total'))['total'] or 0

    # Ingresos diarios en el rango
    daily_revenue = all_in_range.extra(
        select={'day': "CAST(date_time AS DATE)"}
    ).values('day').annotate(total=Sum('total')).order_by('day')

    daily_data = []
    for entry in daily_revenue:
        day_str = entry['day'].strftime('%d/%m') if hasattr(entry['day'], 'strftime') else str(entry['day'])
        daily_data.append({'day': day_str, 'revenue': float(entry['total'])})

    # Ingresos mensuales (últimos 6 meses)
    current_date = today.replace(day=1)
    six_months_ago = current_date - timedelta(days=180)
    monthly_data = Sale.objects.filter(
        base_filter, date_time__date__gte=six_months_ago
    ).extra(
        select={'month': "CAST(DATE_TRUNC('month', date_time) AS DATE)"}
    ).values('month').annotate(total=Sum('total')).order_by('month')

    monthly_dict = {}
    for item in monthly_data:
        m = item['month']
        if hasattr(m, 'strftime'):
            monthly_dict[m.strftime('%Y-%m')] = float(item['total'])

    month_names = {1: 'Ene', 2: 'Feb', 3: 'Mar', 4: 'Abr', 5: 'May', 6: 'Jun',
                   7: 'Jul', 8: 'Ago', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dic'}
    monthly_revenue = []
    for _ in range(6):
        month_total = monthly_dict.get(current_date.strftime('%Y-%m'), 0)
        monthly_revenue.insert(0, {'month': month_names[current_date.month], 'revenue': month_total})
        if current_date.month == 1:
            current_date = current_date.replace(year=current_date.year - 1, month=12)
        else:
            current_date = current_date.replace(month=current_date.month - 1)

    data = {
        'revenue_range': float(revenue_range),
        'revenue_today': float(revenue_today),
        'transactions_range': transactions_range,
        'average_ticket': float(avg_ticket),
        'sales_today_count': sales_today.count(),
        'user_sales_today_count': user_sales_count,
        'user_sales_today_revenue': float(user_sales_revenue),
        'payment_breakdown': list(payment_breakdown),
        'top_products': list(top_products),
        'top_services': list(top_services),
        'daily_revenue': daily_data,
        'monthly_revenue': monthly_revenue,
        'filter_range': {'start': start_date.isoformat(), 'end': end_date.isoformat()},
    }

    cache.set(cache_key, data, 60)
    return Response(data)

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def active_promotions(request):
    """Promociones activas filtradas por tenant"""
    now = timezone.now()
    qs = Promotion.objects.filter(is_active=True, start_date__lte=now, end_date__gte=now)
    tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
    if tenant:
        qs = qs.filter(tenant=tenant)
    else:
        qs = Promotion.objects.none()

    serializer = PromotionSerializer(qs, many=True)
    from apps.utils.response_formatter import StandardResponse
    return Response(StandardResponse.list_response(
        results=serializer.data,
        count=len(serializer.data)
    ))

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def pos_categories(request):
    """Categorías para filtros del POS"""
    try:
        from apps.inventory_api.models import Product
        
        # Obtener categorías de productos (Service no tiene category)
        tenant = getattr(request, 'tenant', None) or getattr(request.user, 'tenant', None)
        if not tenant:
            return Response({'categories': [{'name': 'Todas', 'value': ''}]})
        
        qs = Product.objects.filter(
            tenant=tenant,
            is_active=True,
            category__isnull=False
        ).exclude(category='')
        product_categories = list(qs.values_list('category', flat=True).distinct())
        
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

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
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
