from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.http import HttpResponse
from django.db.models import Sum, Count, Q, Prefetch
from django.utils import timezone
from django.db import transaction
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Employee
from .earnings_models import Earning, FortnightSummary, PeriodSummary, PayrollBatch, PayrollBatchItem
from .earnings_serializers import (
    PayrollBatchSerializer, PayrollBatchCreateSerializer, 
    PayrollBatchProcessSerializer, PayrollBatchListSerializer
)
from .utils import compute_period_range, date_to_year_fortnight
import logging

logger = logging.getLogger(__name__)

class EarningViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def update_employee_config(self, request):
        """Actualizar configuración de pago de empleado"""
        try:
            employee_id = request.data.get('employee_id')
            if not employee_id:
                return Response({'error': 'employee_id requerido'}, status=400)
            
            # Validar empleado y tenant
            employee_filter = {'id': employee_id}
            if not request.user.is_superuser:
                employee_filter['tenant'] = request.user.tenant
            
            employee = Employee.objects.get(**employee_filter)
            
            # Validar salary_type (payment_type)
            if 'payment_type' in request.data or 'salary_type' in request.data:
                salary_type = request.data.get('salary_type') or request.data.get('payment_type')
                if salary_type not in ['commission', 'fixed', 'mixed']:
                    return Response({'error': 'salary_type debe ser: commission, fixed o mixed'}, status=400)
                employee.salary_type = salary_type
            
            # Validar commission_percentage (commission_rate)
            if 'commission_rate' in request.data or 'commission_percentage' in request.data:
                try:
                    commission_percentage = float(
                        request.data.get('commission_percentage') or request.data.get('commission_rate')
                    )
                    if commission_percentage < 0 or commission_percentage > 100:
                        return Response({'error': 'commission_percentage debe estar entre 0 y 100'}, status=400)
                    employee.commission_percentage = commission_percentage
                except (ValueError, TypeError):
                    return Response({'error': 'commission_percentage debe ser un número válido'}, status=400)
            
            # Validar contractual_monthly_salary (salary_amount para compatibilidad)
            if 'contractual_monthly_salary' in request.data or 'salary_amount' in request.data or 'fixed_salary' in request.data:
                try:
                    salary_amount = float(
                        request.data.get('contractual_monthly_salary') or 
                        request.data.get('salary_amount') or 
                        request.data.get('fixed_salary')
                    )
                    if salary_amount < 0:
                        return Response({'error': 'contractual_monthly_salary no puede ser negativo'}, status=400)
                    employee.contractual_monthly_salary = salary_amount
                    # Mantener compatibilidad con salary_amount
                    employee.salary_amount = salary_amount
                except (ValueError, TypeError):
                    return Response({'error': 'contractual_monthly_salary debe ser un número válido'}, status=400)
            
            # Configuración de descuentos legales
            if 'apply_afp' in request.data:
                employee.apply_afp = bool(request.data.get('apply_afp'))
            if 'apply_sfs' in request.data:
                employee.apply_sfs = bool(request.data.get('apply_sfs'))
            if 'apply_isr' in request.data:
                employee.apply_isr = bool(request.data.get('apply_isr'))
            
            employee.save()
            
            return Response({
                'message': 'Configuración actualizada correctamente',
                'employee': {
                    'id': employee.id,
                    'salary_type': employee.salary_type,
                    'commission_percentage': float(employee.commission_percentage or 0),
                    'contractual_monthly_salary': float(employee.contractual_monthly_salary or 0),
                    # Compatibilidad con nombres anteriores
                    'payment_type': employee.salary_type,
                    'commission_rate': float(employee.commission_percentage or 0),
                    'salary_amount': float(employee.salary_amount or 0),
                    'fixed_salary': float(employee.contractual_monthly_salary or 0)
                }
            })
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': f'Error interno: {str(e)}'}, status=500)
    
    @action(detail=False, methods=['post'])
    def pay(self, request):
        """Procesar pago de empleado por sale_ids o quincena"""
        employee_id = request.data.get('employee_id')
        sale_ids = request.data.get('sale_ids', [])
        year = request.data.get('year')
        fortnight = request.data.get('fortnight')
        payment_method = request.data.get('payment_method', 'cash')
        payment_reference = request.data.get('payment_reference', '')
        payment_notes = request.data.get('payment_notes', '')
        idempotency_key = request.data.get('idempotency_key', '')
        
        # Fallback: Accept frequency + reference_date and convert to year/fortnight
        # This is temporary while frontend normalizes to use year/fortnight directly
        if not year or not fortnight:
            frequency = request.data.get('frequency')
            reference_date = request.data.get('reference_date')
            
            if frequency and reference_date:
                # Validate frequency
                if frequency != 'fortnightly':
                    return Response({
                        'error': f'Unsupported frequency: {frequency}. Only "fortnightly" is supported.'
                    }, status=400)
                
                try:
                    year, fortnight = date_to_year_fortnight(reference_date)
                    logger.debug(f"Fallback conversion: frequency={frequency}, reference_date={reference_date} -> year={year}, fortnight={fortnight}")
                except ValueError as e:
                    return Response({'error': str(e)}, status=400)
            else:
                return Response({'error': 'year y fortnight son requeridos (o frequency y reference_date)'}, status=400)
        
        if not employee_id:
            return Response({'error': 'employee_id es requerido'}, status=400)
        
        try:
            year = int(year)
            fortnight = int(fortnight)
            if not (1 <= fortnight <= 24):
                return Response({'error': 'fortnight debe estar entre 1 y 24'}, status=400)
        except ValueError:
            return Response({'error': 'year y fortnight deben ser números enteros'}, status=400)
        
        try:
            employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
            
            with transaction.atomic():
                # IDEMPOTENCIA: Verificar si ya existe pago con mismo idempotency_key
                if idempotency_key:
                    existing = FortnightSummary.objects.filter(
                        employee=employee,
                        payment_reference=idempotency_key,
                        is_paid=True
                    ).first()
                    if existing:
                        return Response({
                            'status': 'already_paid',
                            'message': 'Pago ya procesado anteriormente',
                            'batch_id': existing.id,
                            'paid_at': existing.paid_at.isoformat() if existing.paid_at else None
                        }, status=200)
                
                # Si se envían sale_ids, usar esos; si no, buscar por quincena
                if sale_ids:
                    from apps.pos_api.models import Sale
                    # SELECT FOR UPDATE para evitar race conditions
                    sales = Sale.objects.select_for_update().filter(
                        id__in=sale_ids,
                        employee=employee,
                        status='completed',
                        period__isnull=True  # Solo ventas no pagadas
                    )
                    
                    if not sales.exists():
                        return Response({'error': 'No hay ventas pendientes con los IDs proporcionados'}, status=400)
                    
                    # Calcular total según configuración del empleado
                    total_sales = sum([float(s.total) for s in sales])
                    if employee.salary_type == 'commission':
                        total_earned = total_sales * float(employee.commission_percentage) / 100
                    elif employee.salary_type == 'mixed':
                        commission = total_sales * float(employee.commission_percentage) / 100
                        total_earned = commission
                    else:
                        total_earned = 0
                    
                    services_count = sales.count()
                    
                    # Calcular fechas del período para el summary
                    today = timezone.now().date()
                    year, fortnight = Earning.calculate_fortnight(today)
                    
                    # Crear o actualizar FortnightSummary
                    summary, created = FortnightSummary.objects.get_or_create(
                        employee=employee,
                        fortnight_year=year,
                        fortnight_number=fortnight,
                        defaults={
                            'total_earnings': 0,
                            'total_services': 0,
                            'is_paid': False
                        }
                    )
                    
                    # Asignar ventas al summary
                    for sale in sales:
                        sale.period = summary
                        sale.save()
                    
                    # Actualizar totales del summary
                    summary.total_services += services_count
                    summary.total_earnings += Decimal(str(total_earned))
                    
                    # Aplicar descuentos si corresponde
                    is_end_of_month = (fortnight % 2) == 0
                    should_apply_deductions = (
                        is_end_of_month and 
                        (employee.apply_afp or employee.apply_sfs or employee.apply_isr)
                    )
                    
                    if should_apply_deductions:
                        from .payroll_calculator import calculate_net_salary
                        net_salary, deductions = calculate_net_salary(
                            summary.total_earnings,
                            is_fortnight=True,
                            apply_afp=employee.apply_afp,
                            apply_sfs=employee.apply_sfs,
                            apply_isr=employee.apply_isr
                        )
                        summary.afp_deduction = deductions['afp']
                        summary.sfs_deduction = deductions['sfs']
                        summary.isr_deduction = deductions['isr']
                        summary.total_deductions = deductions['total']
                        summary.net_salary = net_salary
                        summary.amount_paid = net_salary
                    else:
                        summary.net_salary = summary.total_earnings
                        summary.amount_paid = summary.total_earnings
                        summary.afp_deduction = Decimal('0')
                        summary.sfs_deduction = Decimal('0')
                        summary.isr_deduction = Decimal('0')
                        summary.total_deductions = Decimal('0')
                    
                    # Marcar como pagado
                    summary.is_paid = True
                    summary.paid_at = timezone.now()
                    summary.paid_by = request.user
                    summary.payment_method = payment_method
                    summary.payment_reference = idempotency_key or payment_reference
                    summary.payment_notes = payment_notes
                    summary.save()
                    
                    # Crear recibo
                    from .earnings_models import PaymentReceipt
                    receipt = PaymentReceipt.objects.create(fortnight_summary=summary)
                    
                    return Response({
                        'status': 'paid',
                        'message': 'Pago procesado correctamente',
                        'summary': {
                            'employee_id': employee.id,
                            'employee_name': employee.user.full_name or employee.user.email,
                            'sale_ids': sale_ids,
                            'year': year,
                            'fortnight': fortnight,
                            'gross_amount': float(summary.total_earnings),
                            'deductions': {
                                'afp': float(summary.afp_deduction),
                                'sfs': float(summary.sfs_deduction),
                                'isr': float(summary.isr_deduction),
                                'total': float(summary.total_deductions)
                            },
                            'net_amount': float(summary.net_salary),
                            'amount_paid': float(summary.amount_paid),
                            'services_count': services_count,
                            'payment_method': payment_method,
                            'payment_reference': payment_reference,
                            'receipt_number': receipt.receipt_number,
                            'paid_at': summary.paid_at.isoformat()
                        }
                    })
                else:
                    # Flujo original por quincena
                    try:
                        summary = FortnightSummary.objects.get(
                            employee=employee,
                            fortnight_year=year,
                            fortnight_number=fortnight
                        )
                        
                        if summary.is_paid:
                            return Response({
                                'status': 'already_paid',
                                'message': 'La quincena ya está pagada',
                                'batch_id': summary.id,
                                'paid_at': summary.paid_at.isoformat() if summary.paid_at else None
                            }, status=409)  # 409 Conflict en lugar de 400
                            
                    except FortnightSummary.DoesNotExist:
                        return Response({'error': 'No hay ganancias registradas para esta quincena'}, status=404)
                
                # Verificar que hay ganancias para pagar
                if summary.total_earnings <= 0:
                    return Response({'error': 'No hay ganancias para procesar el pago'}, status=400)
                
                # Calcular descuentos legales solo si están habilitados y es fin de mes
                from .payroll_calculator import calculate_net_salary
                
                # Verificar si es fin de mes (quincena 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22, 24)
                is_end_of_month = (fortnight % 2) == 0
                
                # Aplicar descuentos solo si el empleado los tiene habilitados Y es fin de mes
                should_apply_deductions = (
                    is_end_of_month and 
                    (employee.apply_afp or employee.apply_sfs or employee.apply_isr)
                )
                
                if should_apply_deductions:
                    net_salary, deductions = calculate_net_salary(
                        summary.total_earnings, 
                        is_fortnight=True,
                        apply_afp=employee.apply_afp,
                        apply_sfs=employee.apply_sfs,
                        apply_isr=employee.apply_isr
                    )
                else:
                    # Sin descuentos
                    net_salary = summary.total_earnings
                    deductions = {'afp': 0, 'sfs': 0, 'isr': 0, 'total': 0}
                
                # Marcar como pagado con descuentos calculados
                summary.is_paid = True
                summary.paid_at = timezone.now()
                summary.paid_by = request.user
                summary.closed_at = timezone.now()
                summary.payment_method = payment_method
                summary.afp_deduction = deductions['afp']
                summary.sfs_deduction = deductions['sfs']
                summary.isr_deduction = deductions['isr']
                summary.total_deductions = deductions['total']
                summary.net_salary = net_salary
                summary.amount_paid = net_salary  # Pagar el neto
                summary.payment_reference = payment_reference
                summary.payment_notes = payment_notes
                summary.save()
                
                # Crear recibo
                from .earnings_models import PaymentReceipt
                receipt = PaymentReceipt.objects.create(fortnight_summary=summary)
                
                return Response({
                    'status': 'paid',
                    'message': 'Pago procesado correctamente',
                    'summary': {
                        'employee_id': employee.id,
                        'employee_name': employee.user.full_name or employee.user.email,
                        'year': year,
                        'fortnight': fortnight,
                        'gross_amount': float(summary.total_earnings),
                        'deductions': {
                            'afp': float(summary.afp_deduction),
                            'sfs': float(summary.sfs_deduction),
                            'isr': float(summary.isr_deduction),
                            'total': float(summary.total_deductions)
                        },
                        'net_amount': float(summary.net_salary),
                        'amount_paid': float(summary.amount_paid),
                        'services_count': summary.total_services,
                        'payment_method': payment_method,
                        'payment_reference': payment_reference,
                        'receipt_number': receipt.receipt_number,
                        'paid_at': summary.paid_at.isoformat()
                    }
                })
        
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
            
        except Exception as e:
            return Response({'error': f'Error procesando pago: {str(e)}'}, status=500)
    
    def list(self, request):
        """Obtener ganancias por quincena"""
        # Parámetros requeridos: year y fortnight
        year = request.GET.get('year')
        fortnight = request.GET.get('fortnight')
        role = request.GET.get('role')
        status_filter = request.GET.get('status')
        
        # Fallback: Accept frequency + reference_date and convert to year/fortnight
        # This is temporary while frontend normalizes to use year/fortnight directly
        if not year or not fortnight:
            frequency = request.GET.get('frequency')
            reference_date = request.GET.get('reference_date')
            
            if frequency and reference_date:
                # Validate frequency
                if frequency != 'fortnightly':
                    return Response({
                        'error': f'Unsupported frequency: {frequency}. Only "fortnightly" is supported.'
                    }, status=400)
                
                try:
                    year, fortnight = date_to_year_fortnight(reference_date)
                    logger.debug(f"Fallback conversion: frequency={frequency}, reference_date={reference_date} -> year={year}, fortnight={fortnight}")
                except ValueError as e:
                    return Response({'error': str(e)}, status=400)
            else:
                # Si no se especifica year/fortnight ni frequency/reference_date, usar quincena actual
                today = timezone.now().date()
                year, fortnight = Earning.calculate_fortnight(today)
        
        # Validate year/fortnight values
        try:
            year = int(year)
            fortnight = int(fortnight)
            if not (1 <= fortnight <= 24):
                return Response({'error': 'Fortnight debe estar entre 1 y 24'}, status=400)
        except ValueError:
            return Response({'error': 'Year y fortnight deben ser números enteros'}, status=400)
        
        # Calcular fechas del período
        month = ((fortnight - 1) // 2) + 1
        is_first_half = (fortnight % 2) == 1
        
        if is_first_half:
            start_date = datetime(year, month, 1).date()
            end_date = datetime(year, month, 15).date()
        else:
            start_date = datetime(year, month, 16).date()
            if month == 12:
                next_month = datetime(year + 1, 1, 1)
            else:
                next_month = datetime(year, month + 1, 1)
            end_date = (next_month - timedelta(days=1)).date()
        
        # Obtener empleados activos del tenant
        employees = Employee.objects.filter(
            tenant=request.user.tenant,
            is_active=True
        ).select_related('user')
        
        # Obtener FortnightSummary para la quincena especificada
        fortnight_summaries = FortnightSummary.objects.filter(
            employee__tenant=request.user.tenant,
            fortnight_year=year,
            fortnight_number=fortnight
        ).select_related('employee__user')
        
        # Crear diccionario para acceso rápido
        summaries_dict = {summary.employee_id: summary for summary in fortnight_summaries}
        
        earnings_data = []
        
        for emp in employees:
            # Mapear specialty a role
            role_mapped = self._map_specialty_to_role(emp.specialty)
            
            # Filtrar por rol si se especifica
            if role and role_mapped != role:
                continue
            
            logger.info(f"Procesando empleado: {emp.user.full_name or emp.user.email} (ID: {emp.id})")
            
            # Obtener o crear FortnightSummary del empleado
            summary = summaries_dict.get(emp.id)
            
            # Calcular ventas del período
            from apps.pos_api.models import Sale
            sales_data = Sale.objects.filter(
                employee=emp,
                date_time__date__gte=start_date,
                date_time__date__lte=end_date,
                status='completed'
            ).aggregate(
                total_sales=Sum('total'),
                services_count=Count('id')
            )
            
            total_sales = float(sales_data['total_sales'] or 0)
            services_count = sales_data['services_count'] or 0
            
            # Calcular ganancias según tipo de empleado
            total_earned = self._calculate_earnings_by_type(emp, total_sales, start_date, end_date)
            
            if not summary:
                # Crear FortnightSummary si hay ganancias o es sueldo fijo
                if total_earned > 0 or emp.salary_type == 'fixed':
                    logger.info(f"Creando FortnightSummary para {emp.user.full_name}: ${total_earned}, {services_count} servicios")
                    summary = FortnightSummary.objects.create(
                        employee=emp,
                        fortnight_year=year,
                        fortnight_number=fortnight,
                        total_earnings=total_earned,
                        total_services=services_count,
                        is_paid=False
                    )
                    summaries_dict[emp.id] = summary
            else:
                # CRÍTICO: NO actualizar FortnightSummary si ya está pagado
                # Las ventas de un período pagado deben quedar congeladas
                if not summary.is_paid:
                    summary.total_earnings = total_earned
                    summary.total_services = services_count
                    summary.save()
                    logger.info(f"Actualizado FortnightSummary para {emp.user.full_name}: ${total_earned}, {services_count} servicios")
                else:
                    # Si el período ya está pagado, usar los valores guardados (no recalcular)
                    total_earned = float(summary.total_earnings)
                    services_count = summary.total_services
                    logger.info(f"FortnightSummary ya pagado para {emp.user.full_name}: ${total_earned} (no se actualiza)")
            
            if summary:
                # Si el período está pagado, mostrar tanto lo pagado como lo pendiente
                if summary.is_paid:
                    # Lo que está en el summary es lo PAGADO
                    amount_paid = float(summary.total_earnings)
                    # Lo calculado es el TOTAL GENERADO (incluyendo ventas posteriores)
                    total_earned = total_earned
                    # Si hay diferencia, hay monto pendiente
                    if total_earned > amount_paid:
                        payment_status = 'partial'  # Parcialmente pagado
                    else:
                        payment_status = 'paid'
                else:
                    # Período no pagado, todo es pendiente
                    total_earned = float(summary.total_earnings)
                    services_count = summary.total_services
                    payment_status = 'pending'
            else:
                # No hay summary y no se creó (comisión sin ventas)
                total_earned = 0.0
                services_count = 0
                payment_status = 'pending'
            
            # Filtrar por estado si se especifica
            if status_filter and payment_status != status_filter:
                continue
            
            # Calcular monto pagado y pendiente
            if summary and summary.is_paid:
                amount_paid = float(summary.total_earnings)
                amount_pending = max(0, total_earned - amount_paid)
            else:
                amount_paid = 0
                amount_pending = total_earned
            
            earnings_data.append({
                'id': emp.id,
                'user_id': emp.user.id,
                'full_name': emp.user.full_name or emp.user.email,
                'email': emp.user.email,
                'role': role_mapped,
                'is_active': emp.is_active,
                'payment_type': emp.salary_type or 'commission',
                'commission_rate': float(emp.commission_percentage or 40),
                'fixed_salary': float(emp.salary_amount or 0),
                'total_earned': total_earned,
                'amount_paid': amount_paid,
                'amount_pending': amount_pending,
                'services_count': services_count,
                'payment_status': payment_status,
                'fortnight_year': year,
                'fortnight_number': fortnight
            })
        
        # Calcular totales
        total_earned_sum = sum(emp['total_earned'] for emp in earnings_data)
        total_paid = sum(emp['total_earned'] for emp in earnings_data if emp['payment_status'] == 'paid')
        total_pending = sum(emp['total_earned'] for emp in earnings_data if emp['payment_status'] == 'pending')
        
        period_display = f"{start_date} - {end_date}"
        
        return Response({
            'employees': earnings_data,
            'summary': {
                'total_earned': total_earned_sum,
                'total_paid': total_paid,
                'total_pending': total_pending,
                'period': period_display,
                'year': year,
                'fortnight': fortnight,
                'employees_count': len(earnings_data)
            }
        })
    
    def _map_specialty_to_role(self, specialty):
        """Mapea specialty a role"""
        if not specialty:
            return 'stylist'
        
        specialty_lower = specialty.lower()
        if ('admin' in specialty_lower or 'gerente' in specialty_lower or 
            'barber' in specialty_lower or 'barbero' in specialty_lower):
            return 'manager'
        elif ('caja' in specialty_lower or 'limpieza' in specialty_lower or 
              'asistente' in specialty_lower or 'soporte' in specialty_lower):
            return 'assistant'
        elif 'corte' in specialty_lower:
            return 'stylist'
        else:
            return 'stylist'
    
    def _calculate_earnings_by_type(self, employee, total_sales, start_date, end_date):
        """Calcula ganancias según tipo de pago del empleado"""
        from .payroll_utils import convert_salary_to_period
        
        payment_type = employee.salary_type or 'commission'
        commission_rate = float(employee.commission_percentage or 40)
        
        # NUEVO: Usar contractual_monthly_salary como fuente de verdad
        contractual_monthly = Decimal(str(employee.contractual_monthly_salary or 0))
        payment_frequency = employee.payment_frequency or 'biweekly'
        
        if payment_type == 'commission':
            total_earned = (total_sales * commission_rate) / 100
        elif payment_type == 'mixed':
            # Comisión sobre ventas
            commission_earned = (total_sales * commission_rate) / 100
            
            # Sueldo fijo basado en contractual_monthly_salary y payment_frequency
            period_salary = convert_salary_to_period(contractual_monthly, payment_frequency)
            
            # Prorratear si el período no es completo
            days_in_period = (end_date - start_date).days + 1
            
            if payment_frequency == 'biweekly':
                expected_days = 15
            elif payment_frequency == 'monthly':
                expected_days = 30
            elif payment_frequency == 'weekly':
                expected_days = 7
            else:
                expected_days = 1
            
            if days_in_period < expected_days:
                prorated_salary = float(period_salary) * (days_in_period / expected_days)
            else:
                prorated_salary = float(period_salary)
            
            total_earned = prorated_salary + commission_earned
        else:  # fixed
            # Sueldo fijo basado en contractual_monthly_salary
            period_salary = convert_salary_to_period(contractual_monthly, payment_frequency)
            
            # Prorratear si el período no es completo
            days_in_period = (end_date - start_date).days + 1
            
            if payment_frequency == 'biweekly':
                expected_days = 15
            elif payment_frequency == 'monthly':
                expected_days = 30
            elif payment_frequency == 'weekly':
                expected_days = 7
            else:
                expected_days = 1
            
            if days_in_period < expected_days:
                total_earned = float(period_salary) * (days_in_period / expected_days)
            else:
                total_earned = float(period_salary)
        
        return float(total_earned)
    
    def _get_payment_status(self, employee, start_date, end_date, status_filter):
        """Obtiene el estado de pago del empleado para el período"""
        from apps.pos_api.models import Sale
        
        # Verificar si hay ventas PENDIENTES (no cerradas) en el período
        pending_sales = Sale.objects.filter(
            employee=employee,
            date_time__date__gte=start_date,
            date_time__date__lte=end_date,
            status='completed'
        ).filter(
            Q(period__isnull=True) | Q(period__closed_at__isnull=True)
        ).exists()
        
        if pending_sales:
            return 'pending'
        
        # Verificar si hay ventas PAGADAS (cerradas) en el período
        paid_sales = Sale.objects.filter(
            employee=employee,
            date_time__date__gte=start_date,
            date_time__date__lte=end_date,
            status='completed',
            period__closed_at__isnull=False,
            period__is_paid=True
        ).exists()
        
        if paid_sales:
            return 'paid'
        
        # Si no hay ventas en el período, no mostrar el empleado
        return 'no_sales'
    
    def _calculate_fortnight_number(self, date):
        """Calcula el número de quincena (1-24)"""
        from .earnings_models import Earning
        _, fortnight_number = Earning.calculate_fortnight(date)
        return fortnight_number
    
    @action(detail=False, methods=['post'], url_path='(?P<employee_id>[^/.]+)/process_payment')
    def process_payment(self, request, employee_id=None):
        """Procesar pago individual con detalles completos"""
        try:
            employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
            
            # Validar datos requeridos
            period_id = request.data.get('period_id')
            payment_method = request.data.get('payment_method')
            amount_paid = request.data.get('amount_paid')
            
            if not period_id:
                return Response({'error': 'period_id es requerido'}, status=400)
            if not payment_method:
                return Response({'error': 'payment_method es requerido'}, status=400)
            if not amount_paid:
                return Response({'error': 'amount_paid es requerido'}, status=400)
            
            try:
                summary = FortnightSummary.objects.get(id=period_id, employee=employee)
            except FortnightSummary.DoesNotExist:
                return Response({'error': 'Período no encontrado'}, status=404)
            
            if summary.closed_at:
                return Response({'error': 'El período ya está cerrado'}, status=400)
            
            if summary.is_paid:
                return Response({'error': 'El período ya está pagado'}, status=400)
            
            # Validar monto mínimo
            amount_paid = float(amount_paid)
            if amount_paid <= 0:
                return Response({'error': 'El monto debe ser mayor a 0'}, status=400)
            
            # Procesar pago
            summary.is_paid = True
            summary.paid_at = timezone.now()
            summary.paid_by = request.user
            summary.closed_at = timezone.now()
            summary.payment_method = payment_method
            summary.amount_paid = amount_paid
            summary.payment_reference = request.data.get('payment_reference', '')
            summary.payment_notes = request.data.get('payment_notes', '')
            summary.save()
            
            # Generar recibo
            from .earnings_models import PaymentReceipt
            receipt = PaymentReceipt.objects.create(fortnight_summary=summary)
            
            return Response({
                'status': 'paid',
                'message': 'Pago procesado correctamente',
                'summary': {
                    'period_id': summary.id,
                    'amount_paid': float(summary.amount_paid),
                    'payment_method': summary.payment_method,
                    'payment_reference': summary.payment_reference,
                    'receipt_number': receipt.receipt_number,
                    'paid_at': summary.paid_at.isoformat()
                }
            })
            
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': f'Error interno: {str(e)}'}, status=500)
    
    @action(detail=False, methods=['post'], url_path='(?P<employee_id>[^/.]+)/reverse_payment')
    def reverse_payment(self, request, employee_id=None):
        """Revertir pago si está permitido"""
        try:
            employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
            period_id = request.data.get('period_id')
            
            if not period_id:
                return Response({'error': 'period_id es requerido'}, status=400)
            
            try:
                summary = FortnightSummary.objects.get(id=period_id, employee=employee)
            except FortnightSummary.DoesNotExist:
                return Response({'error': 'Período no encontrado'}, status=404)
            
            if not summary.is_paid:
                return Response({'error': 'El período no está pagado'}, status=400)
            
            # Validar que no sea muy antiguo (máximo 30 días)
            if summary.paid_at and (timezone.now() - summary.paid_at).days > 30:
                return Response({'error': 'No se puede revertir un pago de más de 30 días'}, status=400)
            
            # Revertir pago
            summary.is_paid = False
            summary.paid_at = None
            summary.paid_by = None
            summary.closed_at = None
            summary.payment_method = None
            summary.amount_paid = None
            summary.payment_reference = None
            summary.payment_notes = None
            summary.save()
            
            # Eliminar recibo si existe
            if hasattr(summary, 'receipt'):
                summary.receipt.delete()
            
            return Response({
                'status': 'reversed',
                'message': 'Pago revertido correctamente',
                'period_id': summary.id
            })
            
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': f'Error interno: {str(e)}'}, status=500)
    
    @action(detail=False, methods=['patch'], url_path='(?P<employee_id>[^/.]+)/mark_paid')
    def mark_paid(self, request, employee_id=None):
        """Marcar empleado como pagado"""
        try:
            employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
            
            # Opción 1: Marcar por período específico (ID)
            period_id = request.data.get('period_id')
            if period_id:
                try:
                    summary = FortnightSummary.objects.get(
                        id=period_id,
                        employee=employee
                    )
                    
                    if summary.closed_at:
                        return Response({'error': 'El período ya está cerrado y no puede modificarse'}, status=400)
                    
                    # Calcular ganancias del período
                    from apps.pos_api.models import Sale
                    sales_data = Sale.objects.filter(
                        period=summary
                    ).aggregate(
                        total_sales=Sum('total'),
                        services_count=Count('id')
                    )
                    
                    total_sales = float(sales_data['total_sales'] or 0)
                    services_count = sales_data['services_count'] or 0
                    
                    if total_sales == 0 and services_count == 0:
                        return Response({'error': 'No se puede marcar como pagado un período sin ventas'}, status=400)
                    
                    # Calcular fechas del período para _calculate_earnings_by_type
                    month = ((summary.fortnight_number - 1) // 2) + 1
                    is_first_half = (summary.fortnight_number % 2) == 1
                    
                    if is_first_half:
                        start_date = datetime(summary.fortnight_year, month, 1).date()
                        end_date = datetime(summary.fortnight_year, month, 15).date()
                    else:
                        start_date = datetime(summary.fortnight_year, month, 16).date()
                        if month == 12:
                            next_month = datetime(summary.fortnight_year + 1, 1, 1)
                        else:
                            next_month = datetime(summary.fortnight_year, month + 1, 1)
                        last_day = (next_month - timedelta(days=1)).day
                        end_date = datetime(summary.fortnight_year, month, last_day).date()
                    
                    total_earned = self._calculate_earnings_by_type(employee, total_sales, start_date, end_date)
                    
                    # Marcar como pagado y cerrar
                    summary.total_earnings = total_earned
                    summary.total_services = services_count
                    summary.is_paid = True
                    summary.paid_at = timezone.now()
                    summary.paid_by = request.user
                    summary.closed_at = timezone.now()
                    summary.save()
                    
                    return Response({
                        'status': 'paid',
                        'message': 'Pago marcado correctamente',
                        'summary': {
                            'period_id': summary.id,
                            'fortnight_display': summary.fortnight_display,
                            'amount': float(summary.total_earnings),
                            'services': summary.total_services,
                            'paid_at': summary.paid_at.isoformat()
                        }
                    })
                    
                except FortnightSummary.DoesNotExist:
                    return Response({'error': 'Período no encontrado'}, status=404)
            
            # Opción 2: Marcar por fechas (método original mejorado)
            period_start = request.data.get('period_start')
            period_end = request.data.get('period_end')
            
            if not period_start or not period_end:
                return Response({'error': 'Se requiere period_id o (period_start y period_end)'}, status=400)
            
            try:
                start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
                end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
            except ValueError:
                return Response({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}, status=400)
            
            if start_date > end_date:
                return Response({'error': 'Fecha inicial no puede ser mayor a fecha final'}, status=400)
            
            year = start_date.year
            fortnight_number = self._calculate_fortnight_number(start_date)
            
            # Validar que existan ventas en el período
            from apps.pos_api.models import Sale
            sales_data = Sale.objects.filter(
                employee_id=employee.id,
                date_time__date__gte=start_date,
                date_time__date__lte=end_date,
                status='completed'
            ).aggregate(
                total_sales=Sum('total'),
                services_count=Count('id')
            )
            
            total_sales = float(sales_data['total_sales'] or 0)
            services_count = sales_data['services_count'] or 0
            
            if total_sales == 0 and services_count == 0:
                return Response({'error': 'No se puede marcar como pagado un período sin ventas'}, status=400)
            
            total_earned = self._calculate_earnings_by_type(employee, total_sales, start_date, end_date)
            
            # Crear o actualizar resumen de quincena
            summary, created = FortnightSummary.objects.get_or_create(
                employee=employee,
                fortnight_year=year,
                fortnight_number=fortnight_number,
                defaults={
                    'total_earnings': total_earned,
                    'total_services': services_count,
                    'is_paid': True,
                    'paid_at': timezone.now(),
                    'paid_by': request.user,
                    'closed_at': timezone.now()
                }
            )
            
            if not created:
                if summary.closed_at:
                    return Response({'error': 'El período ya está cerrado y no puede modificarse'}, status=400)
                
                summary.total_earnings = total_earned
                summary.total_services = services_count
                summary.is_paid = True
                summary.paid_at = timezone.now()
                summary.paid_by = request.user
                summary.closed_at = timezone.now()
                summary.save()
            
            # Asignar todas las ventas del período al summary
            Sale.objects.filter(
                employee_id=employee.id,
                date_time__date__gte=start_date,
                date_time__date__lte=end_date,
                status='completed',
                period__isnull=True
            ).update(period=summary)
            
            Sale.objects.filter(
                employee_id=employee.id,
                date_time__date__gte=start_date,
                date_time__date__lte=end_date,
                status='completed',
                period__closed_at__isnull=True
            ).exclude(period=summary).update(period=summary)
            
            return Response({
                'status': 'paid',
                'message': 'Pago marcado correctamente',
                'summary': {
                    'period': f"{period_start} - {period_end}",
                    'amount': float(summary.total_earnings),
                    'services': summary.total_services,
                    'paid_at': summary.paid_at.isoformat()
                }
            })
            
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': f'Error interno: {str(e)}'}, status=500)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Estadísticas reales de ganancias del tenant"""
        from apps.pos_api.models import Sale
        
        # Estadísticas del mes actual
        today = timezone.now().date()
        month_start = today.replace(day=1)
        
        # Filtrar por tenant
        sales_filter = {'date_time__date__gte': month_start, 'date_time__date__lte': today}
        if not request.user.is_superuser and request.user.tenant:
            sales_filter['employee__tenant'] = request.user.tenant
        
        monthly_sales = Sale.objects.filter(**sales_filter).aggregate(total=Sum('total'))['total'] or 0
        
        # Top empleados por ventas del tenant
        top_employees_data = Sale.objects.filter(**sales_filter).values(
            'employee_id', 'employee__user__full_name', 'employee__user__email'
        ).annotate(
            total_sales=Sum('total'),
            sales_count=Count('id')
        ).order_by('-total_sales')[:5]
        
        # Formatear top empleados
        top_employees = []
        for emp_data in top_employees_data:
            if emp_data['employee_id']:  # Solo incluir ventas con empleado asignado
                top_employees.append({
                    'employee_id': emp_data['employee_id'],
                    'name': emp_data['employee__user__full_name'] or emp_data['employee__user__email'],
                    'total_sales': float(emp_data['total_sales']),
                    'sales_count': emp_data['sales_count']
                })
        
        return Response({
            'period': f"{month_start} - {today}",
            'total_generated': float(monthly_sales),
            'total_earned': float(monthly_sales * 0.4),  # Estimado 40% promedio
            'top_employees': top_employees
        })
    
    @action(detail=False, methods=['get'], url_path='(?P<employee_id>[^/.]+)/active_periods')
    def active_periods(self, request, employee_id=None):
        """Obtener períodos activos del empleado"""
        try:
            employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
            
            # Buscar períodos activos (no cerrados) con ventas
            from apps.pos_api.models import Sale
            active_periods = FortnightSummary.objects.filter(
                employee=employee,
                closed_at__isnull=True
            ).annotate(
                sales_count=Count('sales'),
                sales_total=Sum('sales__total')
            ).filter(sales_count__gt=0)
            
            periods_data = []
            for period in active_periods:
                # Calcular fechas del período
                month = ((period.fortnight_number - 1) // 2) + 1
                is_first_half = (period.fortnight_number % 2) == 1
                
                if is_first_half:
                    start_date = datetime(period.fortnight_year, month, 1).date()
                    end_date = datetime(period.fortnight_year, month, 15).date()
                else:
                    start_date = datetime(period.fortnight_year, month, 16).date()
                    if month == 12:
                        next_month = datetime(period.fortnight_year + 1, 1, 1)
                    else:
                        next_month = datetime(period.fortnight_year, month + 1, 1)
                    last_day = (next_month - timedelta(days=1)).day
                    end_date = datetime(period.fortnight_year, month, last_day).date()
                
                # Calcular ganancias
                total_earned = self._calculate_earnings_by_type(
                    employee, 
                    float(period.sales_total or 0), 
                    start_date, 
                    end_date
                )
                
                periods_data.append({
                    'id': period.id,
                    'fortnight_display': period.fortnight_display,
                    'period_dates': f"{start_date} - {end_date}",
                    'total_sales': float(period.sales_total or 0),
                    'total_earned': total_earned,
                    'services_count': period.sales_count,
                    'is_paid': period.is_paid,
                    'can_be_paid': True  # Períodos activos siempre se pueden pagar
                })
            
            return Response({
                'employee_id': employee.id,
                'employee_name': employee.user.full_name or employee.user.email,
                'active_periods': periods_data,
                'total_periods': len(periods_data)
            })
            
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
    
    @action(detail=False, methods=['get'], url_path='(?P<employee_id>[^/.]+)/payment_history')
    def payment_history(self, request, employee_id=None):
        """Historial de pagos del empleado - formato estandarizado"""
        try:
            employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
            
            summaries = FortnightSummary.objects.filter(
                employee=employee,
                is_paid=True
            ).order_by('-fortnight_year', '-fortnight_number')[:12]
            
            history = []
            for summary in summaries:
                # Calcular fechas del período
                month = ((summary.fortnight_number - 1) // 2) + 1
                is_first_half = (summary.fortnight_number % 2) == 1
                
                if is_first_half:
                    period_start = f"{summary.fortnight_year}-{month:02d}-01"
                    period_end = f"{summary.fortnight_year}-{month:02d}-15"
                else:
                    period_start = f"{summary.fortnight_year}-{month:02d}-16"
                    # Último día del mes
                    if month == 12:
                        next_month = datetime(summary.fortnight_year + 1, 1, 1)
                    else:
                        next_month = datetime(summary.fortnight_year, month + 1, 1)
                    last_day = (next_month - timedelta(days=1)).day
                    period_end = f"{summary.fortnight_year}-{month:02d}-{last_day:02d}"
                
                history.append({
                    'id': summary.id,
                    'period': f"{period_start} - {period_end}",
                    'fortnight_display': summary.fortnight_display,
                    'amount': float(summary.total_earnings or 0),
                    'amount_paid': float(summary.amount_paid or 0),
                    'services_count': summary.total_services or 0,
                    'payment_type': employee.payment_type or 'commission',
                    'payment_method': summary.payment_method,
                    'payment_reference': summary.payment_reference,
                    'payment_notes': summary.payment_notes,
                    'paid_at': summary.paid_at.isoformat() if summary.paid_at else None,
                    'paid_by': summary.paid_by.full_name if summary.paid_by and hasattr(summary.paid_by, 'full_name') else (summary.paid_by.email if summary.paid_by else None),
                    'receipt_number': summary.receipt.receipt_number if hasattr(summary, 'receipt') else None,
                    'can_reverse': summary.paid_at and (timezone.now() - summary.paid_at).days <= 30 if summary.paid_at else False
                })
            
            return Response({
                'employee_id': employee.id,
                'employee_name': employee.user.full_name or employee.user.email,
                'payment_history': history,
                'total_records': len(history)
            })
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
    
    @action(detail=False, methods=['post'])
    def send_notifications(self, request):
        """Enviar notificaciones automáticas de pago"""
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Obtener empleados con pagos pendientes
        today = timezone.now().date()
        if today.day <= 15:
            start_date = today.replace(day=1)
            end_date = today.replace(day=15)
        else:
            start_date = today.replace(day=16)
            last_day = (today.replace(month=today.month+1, day=1) - timedelta(days=1)).day
            end_date = today.replace(day=last_day)
        
        employees = Employee.objects.filter(
            tenant=request.user.tenant,
            is_active=True
        ).select_related('user')
        
        notifications_sent = 0
        for emp in employees:
            payment_status = self._get_payment_status(emp, start_date, end_date, None)
            if payment_status == 'pending':
                # Usar nueva estructura de cálculo
                from apps.pos_api.models import Sale
                sales_data = Sale.objects.filter(
                    employee_id=emp.id,
                    date_time__date__gte=start_date,
                    date_time__date__lte=end_date
                ).aggregate(total_sales=Sum('total'))['total_sales'] or 0
                
                total_earned = self._calculate_earnings_by_type(emp, float(sales_data), start_date, end_date)
                
                try:
                    send_mail(
                        subject=f'Pago Quincenal Disponible - {start_date.strftime("%d/%m")} al {end_date.strftime("%d/%m")}',
                        message=f'Hola {emp.user.full_name},\n\nTu pago quincenal está listo: ${total_earned:,.2f}\n\nSaludos,\nEquipo de Administración',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[emp.user.email],
                        fail_silently=True
                    )
                    notifications_sent += 1
                except Exception:
                    pass
        
        return Response({
            'notifications_sent': notifications_sent,
            'message': f'Se enviaron {notifications_sent} notificaciones'
        })
    
    @action(detail=False, methods=['post'])
    def prepare_payroll(self, request):
        """Preparar datos para módulo de payroll futuro"""
        period_start = request.data.get('period_start')
        period_end = request.data.get('period_end')
        employee_ids = request.data.get('employee_ids', [])
        
        if not period_start or not period_end:
            return Response({'error': 'period_start y period_end son requeridos'}, status=400)
        
        try:
            start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
        except ValueError:
            return Response({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}, status=400)
        
        # Filtrar empleados
        employees_query = Employee.objects.filter(
            tenant=request.user.tenant,
            is_active=True
        ).select_related('user')
        
        if employee_ids:
            employees_query = employees_query.filter(id__in=employee_ids)
        
        # Preparar datos para payroll
        payroll_data = []
        for emp in employees_query:
            from apps.pos_api.models import Sale
            sales_data = Sale.objects.filter(
                employee_id=emp.id,
                date_time__date__gte=start_date,
                date_time__date__lte=end_date,
                status='completed'
            ).aggregate(
                total_sales=Sum('total'),
                services_count=Count('id')
            )
            
            total_sales = float(sales_data['total_sales'] or 0)
            services_count = sales_data['services_count'] or 0
            total_earned = self._calculate_earnings_by_type(emp, total_sales, start_date, end_date)
            
            payroll_data.append({
                'employee_id': emp.id,
                'employee_name': emp.user.full_name or emp.user.email,
                'email': emp.user.email,
                'payment_type': emp.payment_type,
                'gross_amount': total_earned,
                'total_sales': total_sales,
                'services_count': services_count,
                'period': f"{start_date} - {end_date}",
                # Campos preparados para payroll futuro
                'tax_deductions': 0,  # Calcular según legislación
                'social_security': 0,  # Calcular según legislación
                'net_amount': total_earned,  # gross_amount - deducciones
                'bank_account': getattr(emp, 'bank_account', ''),
                'tax_id': getattr(emp, 'tax_id', '')
            })
        
        return Response({
            'payroll_data': payroll_data,
            'period': f"{start_date} - {end_date}",
            'total_employees': len(payroll_data),
            'total_gross': sum(item['gross_amount'] for item in payroll_data),
            'ready_for_processing': True
        })
    
    @action(detail=False, methods=['get'])
    def pending_payments(self, request):
        """Obtener todos los empleados con pagos pendientes"""
        from apps.pos_api.models import Sale
        
        employees = Employee.objects.filter(
            tenant=request.user.tenant,
            is_active=True
        ).select_related('user')
        
        pending_data = []
        for emp in employees:
            # Buscar períodos activos con ventas
            active_periods = FortnightSummary.objects.filter(
                employee=emp,
                closed_at__isnull=True
            ).annotate(
                sales_count=Count('sales'),
                sales_total=Sum('sales__total')
            ).filter(sales_count__gt=0)
            
            if active_periods.exists():
                total_pending = 0
                periods_info = []
                
                for period in active_periods:
                    # Calcular fechas del período
                    month = ((period.fortnight_number - 1) // 2) + 1
                    is_first_half = (period.fortnight_number % 2) == 1
                    
                    if is_first_half:
                        start_date = datetime(period.fortnight_year, month, 1).date()
                        end_date = datetime(period.fortnight_year, month, 15).date()
                    else:
                        start_date = datetime(period.fortnight_year, month, 16).date()
                        if month == 12:
                            next_month = datetime(period.fortnight_year + 1, 1, 1)
                        else:
                            next_month = datetime(period.fortnight_year, month + 1, 1)
                        last_day = (next_month - timedelta(days=1)).day
                        end_date = datetime(period.fortnight_year, month, last_day).date()
                    
                    # Calcular ganancias
                    total_earned = self._calculate_earnings_by_type(
                        emp, 
                        float(period.sales_total or 0), 
                        start_date, 
                        end_date
                    )
                    
                    total_pending += total_earned
                    periods_info.append({
                        'period_id': period.id,
                        'fortnight_display': period.fortnight_display,
                        'amount': total_earned,
                        'services': period.sales_count
                    })
                
                pending_data.append({
                    'employee_id': emp.id,
                    'employee_name': emp.user.full_name or emp.user.email,
                    'email': emp.user.email,
                    'payment_type': emp.payment_type,
                    'total_pending': total_pending,
                    'periods': periods_info
                })
        
        return Response({
            'pending_payments': pending_data,
            'total_employees': len(pending_data),
            'total_amount': sum(emp['total_pending'] for emp in pending_data)
        })
    
    @action(detail=False, methods=['post'])
    def calculate_payroll(self, request):
        """Calcular nómina con descuentos legales dominicanos"""
        from .payroll_calculator import get_payroll_summary, validate_minimum_wage
        
        gross_salary = request.data.get('gross_salary')
        is_fortnight = request.data.get('is_fortnight', True)
        company_size = request.data.get('company_size', 'pequena')
        
        if not gross_salary:
            return Response({'error': 'gross_salary es requerido'}, status=400)
        
        try:
            gross_salary = Decimal(str(gross_salary))
        except (ValueError, TypeError):
            return Response({'error': 'gross_salary debe ser un número válido'}, status=400)
        
        # Obtener resumen completo
        summary = get_payroll_summary(gross_salary, is_fortnight)
        
        return Response({
            'calculation': summary,
            'notes': [
                'Descuentos según normativa laboral de República Dominicana',
                'AFP: 2.87% del salario bruto',
                'SFS: 3.04% del salario bruto',
                'ISR: Según escala progresiva (si aplica)'
            ]
        })
    
    @action(detail=False, methods=['post'])
    def fix_data_inconsistencies(self, request):
        """Corregir inconsistencias en los datos de earnings"""
        from apps.pos_api.models import Sale
        
        if not request.user.is_staff:
            return Response({'error': 'Solo administradores pueden ejecutar esta acción'}, status=403)
        
        fixes_applied = []
        
        # 1. Asignar ventas sin período a períodos activos
        sales_without_period = Sale.objects.filter(
            period__isnull=True,
            employee__isnull=False,
            employee__tenant=request.user.tenant,
            status='completed'
        )
        
        for sale in sales_without_period:
            # Buscar período activo para el empleado
            active_period = FortnightSummary.objects.filter(
                employee=sale.employee,
                closed_at__isnull=True
            ).first()
            
            if not active_period:
                # Crear período activo
                date = sale.date_time.date()
                year = date.year
                month = date.month
                day = date.day
                fortnight_in_month = 1 if day <= 15 else 2
                fortnight_number = (month - 1) * 2 + fortnight_in_month
                
                # Verificar si ya existe período cerrado para esta quincena
                existing_closed = FortnightSummary.objects.filter(
                    employee=sale.employee,
                    fortnight_year=year,
                    fortnight_number=fortnight_number,
                    closed_at__isnull=False
                ).exists()
                
                if existing_closed:
                    # Crear período para siguiente quincena
                    if fortnight_number < 24:
                        fortnight_number += 1
                    else:
                        year += 1
                        fortnight_number = 1
                
                active_period = FortnightSummary.objects.create(
                    employee=sale.employee,
                    fortnight_year=year,
                    fortnight_number=fortnight_number,
                    total_earnings=0,
                    total_services=0,
                    is_paid=False
                )
                fixes_applied.append(f'Creado período {active_period.id} para empleado {sale.employee.id}')
            
            sale.period = active_period
            sale.save()
            fixes_applied.append(f'Venta {sale.id} asignada a período {active_period.id}')
        
        # 2. Eliminar períodos vacíos marcados como pagados
        empty_paid_periods = FortnightSummary.objects.filter(
            employee__tenant=request.user.tenant,
            is_paid=True,
            closed_at__isnull=False
        ).annotate(
            sales_count=Count('sales')
        ).filter(sales_count=0)
        
        for period in empty_paid_periods:
            fixes_applied.append(f'Eliminado período vacío {period.id} del empleado {period.employee.id}')
            period.delete()
        
        # 3. Recalcular totales de períodos activos
        active_periods = FortnightSummary.objects.filter(
            employee__tenant=request.user.tenant,
            closed_at__isnull=True
        )
        
        for period in active_periods:
            sales_data = Sale.objects.filter(period=period).aggregate(
                total_sales=Sum('total'),
                services_count=Count('id')
            )
            
            if sales_data['total_sales']:
                # Calcular fechas del período
                month = ((period.fortnight_number - 1) // 2) + 1
                is_first_half = (period.fortnight_number % 2) == 1
                
                if is_first_half:
                    start_date = datetime(period.fortnight_year, month, 1).date()
                    end_date = datetime(period.fortnight_year, month, 15).date()
                else:
                    start_date = datetime(period.fortnight_year, month, 16).date()
                    if month == 12:
                        next_month = datetime(period.fortnight_year + 1, 1, 1)
                    else:
                        next_month = datetime(period.fortnight_year, month + 1, 1)
                    last_day = (next_month - timedelta(days=1)).day
                    end_date = datetime(period.fortnight_year, month, last_day).date()
                
                total_earned = self._calculate_earnings_by_type(
                    period.employee,
                    float(sales_data['total_sales']),
                    start_date,
                    end_date
                )
                
                period.total_earnings = total_earned
                period.total_services = sales_data['services_count']
                period.save()
                
                fixes_applied.append(f'Recalculado período {period.id}: ${total_earned}')
        
        return Response({
            'message': 'Inconsistencias corregidas',
            'fixes_applied': fixes_applied,
            'total_fixes': len(fixes_applied)
        })

    @action(detail=False, methods=['post'])
    def create_payroll_batch(self, request):
        """Crear lote de nómina"""
        serializer = PayrollBatchCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        data = serializer.validated_data
        
        try:
            with transaction.atomic():
                # Crear batch
                batch = PayrollBatch.objects.create(
                    tenant=request.user.tenant,
                    period_start=data['period_start'],
                    period_end=data['period_end'],
                    frequency=data['frequency'],
                    created_by=request.user,
                    status='draft'
                )
                
                # Obtener empleados válidos del tenant
                employees = Employee.objects.filter(
                    id__in=data['employee_ids'],
                    tenant=request.user.tenant,
                    is_active=True
                ).select_related('user')
                
                if not employees.exists():
                    return Response({'error': 'No se encontraron empleados válidos'}, status=400)
                
                total_amount = Decimal('0.00')
                items_created = 0
                
                # Crear items del batch
                for employee in employees:
                    # Calcular ganancias del período
                    from apps.pos_api.models import Sale
                    sales_data = Sale.objects.filter(
                        employee=employee,
                        date_time__date__gte=data['period_start'],
                        date_time__date__lte=data['period_end'],
                        status='completed'
                    ).aggregate(
                        total_sales=Sum('total'),
                        services_count=Count('id')
                    )
                    
                    total_sales = float(sales_data['total_sales'] or 0)
                    
                    # Calcular earnings según tipo de empleado
                    gross_amount = self._calculate_earnings_by_type(
                        employee, total_sales, data['period_start'], data['period_end']
                    )
                    
                    if gross_amount > 0:
                        # Buscar o crear PeriodSummary
                        period_start, period_end, period_year, period_index = compute_period_range(
                            data['frequency'], data['period_start']
                        )
                        
                        period_summary, _ = PeriodSummary.objects.get_or_create(
                            employee=employee,
                            frequency=data['frequency'],
                            period_year=period_year,
                            period_index=period_index,
                            defaults={
                                'period_start': period_start,
                                'period_end': period_end,
                                'total_earnings': gross_amount,
                                'total_services': sales_data['services_count'] or 0
                            }
                        )
                        
                        # Crear item del batch
                        PayrollBatchItem.objects.create(
                            batch=batch,
                            employee=employee,
                            period_summary=period_summary,
                            gross_amount=gross_amount,
                            deductions=Decimal('0.00'),  # TODO: Implementar deducciones
                            net_amount=gross_amount,
                            status='pending'
                        )
                        
                        total_amount += gross_amount
                        items_created += 1
                
                # Actualizar totales del batch
                batch.total_employees = items_created
                batch.total_amount = total_amount
                batch.status = 'approved' if items_created > 0 else 'draft'
                batch.save()
                
                logger.info(f"Batch creado: {batch.batch_number} con {items_created} items")
                
                serializer = PayrollBatchSerializer(batch)
                return Response({
                    'status': 'created',
                    'batch': serializer.data,
                    'items_created': items_created
                })
                
        except Exception as e:
            logger.error(f"Error creando batch: {str(e)}")
            return Response({'error': f'Error interno: {str(e)}'}, status=500)
    
    @action(detail=False, methods=['post'])
    def process_payroll_batch(self, request):
        """Procesar lote de nómina en background"""
        serializer = PayrollBatchProcessSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
        
        batch_id = serializer.validated_data['batch_id']
        
        try:
            batch = PayrollBatch.objects.get(
                id=batch_id,
                tenant=request.user.tenant
            )
            
            if batch.status not in ['approved', 'draft']:
                return Response({'error': 'Batch no puede ser procesado en su estado actual'}, status=400)
            
            # Enqueue background task
            from .tasks import process_payroll_batch_task
            task = process_payroll_batch_task.delay(batch_id)
            
            # Guardar task_id en el batch
            batch.task_id = task.id
            batch.status = 'processing'
            batch.save()
            
            logger.info(f"Batch {batch_id} encolado para procesamiento con task {task.id}")
            
            return Response({
                'status': 'processing',
                'task_id': task.id,
                'batch_id': batch_id
            })
            
        except PayrollBatch.DoesNotExist:
            return Response({'error': 'Batch no encontrado'}, status=404)
        except Exception as e:
            logger.error(f"Error procesando batch {batch_id}: {str(e)}")
            return Response({'error': f'Error interno: {str(e)}'}, status=500)
    
    @action(detail=False, methods=['get'])
    def export_payroll_pdf(self, request):
        """Exportar lote de nómina como PDF"""
        batch_id = request.GET.get('batch_id')
        if not batch_id:
            return Response({'error': 'batch_id es requerido'}, status=400)
        
        try:
            batch = PayrollBatch.objects.select_related('tenant', 'created_by').prefetch_related(
                'items__employee__user'
            ).get(id=batch_id, tenant=request.user.tenant)
            
            # Generar PDF
            from .utils import generate_payroll_batch_pdf
            pdf_content = generate_payroll_batch_pdf(batch)
            
            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="nomina_{batch.batch_number}.pdf"'
            
            logger.info(f"PDF generado para batch {batch_id}")
            return response
            
        except PayrollBatch.DoesNotExist:
            return Response({'error': 'Batch no encontrado'}, status=404)
        except Exception as e:
            logger.error(f"Error generando PDF para batch {batch_id}: {str(e)}")
            return Response({'error': f'Error interno: {str(e)}'}, status=500)
    
    @action(detail=False, methods=['get'])
    def list_payroll_batches(self, request):
        """Listar lotes de nómina del tenant"""
        batches = PayrollBatch.objects.filter(
            tenant=request.user.tenant
        ).select_related('created_by').order_by('-created_at')
        
        serializer = PayrollBatchListSerializer(batches, many=True)
        return Response({
            'batches': serializer.data,
            'count': batches.count()
        })

class FortnightSummaryViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Obtener resúmenes quincenales reales"""
        summaries = FortnightSummary.objects.filter(
            employee__tenant=request.user.tenant
        ).select_related('employee__user').order_by('-fortnight_year', '-fortnight_number')
        
        from .earnings_serializers import FortnightSummarySerializer
        from apps.utils.response_formatter import StandardResponse
        serializer = FortnightSummarySerializer(summaries, many=True)
        return Response(StandardResponse.list_response(
            results=serializer.data,
            count=summaries.count()
        ))
    
    @action(detail=False, methods=['post'])
    def generate_reports(self, request):
        """Generar reportes automáticos de quincena"""
        from django.http import HttpResponse
        import csv
        
        # Obtener parámetros
        year = int(request.data.get('year', timezone.now().year))
        fortnight = int(request.data.get('fortnight', 1))
        
        summaries = FortnightSummary.objects.filter(
            employee__tenant=request.user.tenant,
            fortnight_year=year,
            fortnight_number=fortnight
        ).select_related('employee__user')
        
        # Crear CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="reporte_quincena_{year}_Q{fortnight}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Empleado', 'Email', 'Ganancias', 'Servicios', 'Estado', 'Fecha Pago'])
        
        for summary in summaries:
            writer.writerow([
                summary.employee.user.full_name,
                summary.employee.user.email,
                f"${summary.total_earnings:,.2f}",
                summary.total_services,
                'Pagado' if summary.is_paid else 'Pendiente',
                summary.paid_at.strftime('%d/%m/%Y') if summary.paid_at else 'N/A'
            ])
        
        return response
# ==================== ENDPOINTS DE NÓMINA ====================
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .payroll_services import PayrollService
from .payroll_permissions import IsHROrClientAdmin, CanViewOwnPaystubs
from django.template.loader import render_to_string
from django.http import HttpResponse

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payroll_preview(request):
    """Preview de nómina sin persistir"""
    from .payroll_calculator import get_payroll_summary
    
    gross_salary = request.data.get('gross_salary')
    is_fortnight = request.data.get('is_fortnight', True)
    
    if not gross_salary:
        return Response({'error': 'gross_salary requerido'}, status=400)
    
    try:
        gross = Decimal(str(gross_salary))
        summary = get_payroll_summary(gross, is_fortnight)
        return Response(summary)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsHROrClientAdmin])
def payroll_generate(request):
    """Generar recibos de nómina para un período"""
    year = request.data.get('year')
    fortnight = request.data.get('fortnight')
    employee_ids = request.data.get('employee_ids')
    
    if not year or not fortnight:
        return Response({'error': 'year y fortnight requeridos'}, status=400)
    
    try:
        results = PayrollService.bulk_generate_for_period(
            request.user.tenant,
            int(year),
            int(fortnight),
            employee_ids
        )
        return Response(results)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_my_stubs(request):
    """Empleado lista sus recibos"""
    try:
        employee = Employee.objects.get(user=request.user)
        summaries = FortnightSummary.objects.filter(
            employee=employee,
            is_paid=True
        ).order_by('-fortnight_year', '-fortnight_number')[:12]
        
        data = [{
            'id': s.id,
            'period': s.fortnight_display,
            'gross': float(s.total_earnings),
            'deductions': float(s.total_deductions),
            'net': float(s.net_salary),
            'paid_at': s.paid_at.isoformat() if s.paid_at else None,
            'receipt_number': s.receipt.receipt_number if hasattr(s, 'receipt') else None
        } for s in summaries]
        
        return Response({'stubs': data})
    except Employee.DoesNotExist:
        return Response({'error': 'No es empleado'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_stub_download(request, stub_id):
    """Descargar PDF del recibo"""
    try:
        summary = FortnightSummary.objects.get(id=stub_id)
        
        # Verificar permisos
        if not request.user.is_superuser:
            if summary.employee.user != request.user:
                return Response({'error': 'Sin permisos'}, status=403)
        
        if not summary.is_paid:
            return Response({'error': 'Recibo no pagado'}, status=400)
        
        receipt = PaymentReceipt.objects.get(fortnight_summary=summary)
        
        # Renderizar HTML
        html = render_to_string('payroll/paystub.html', {
            'summary': summary,
            'receipt': receipt,
            'company_name': request.user.tenant.name if request.user.tenant else 'MI EMPRESA',
            'now': timezone.now()
        })
        
        # Retornar HTML (para PDF usar WeasyPrint en producción)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = f'inline; filename="recibo_{receipt.receipt_number}.html"'
        return response
        
    except FortnightSummary.DoesNotExist:
        return Response({'error': 'Recibo no encontrado'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsHROrClientAdmin])
def payroll_mark_paid(request, stub_id):
    """Marcar recibo como pagado"""
    try:
        summary = FortnightSummary.objects.get(id=stub_id)
        
        if summary.is_paid:
            return Response({'error': 'Ya está pagado'}, status=400)
        
        method = request.data.get('payment_method', 'transfer')
        transaction_id = request.data.get('transaction_id', '')
        
        receipt = PayrollService.mark_paystub_as_paid(
            summary,
            timezone.now(),
            method,
            transaction_id
        )
        
        return Response({
            'success': True,
            'receipt_number': receipt.receipt_number,
            'paid_at': summary.paid_at.isoformat()
        })
        
    except FortnightSummary.DoesNotExist:
        return Response({'error': 'Recibo no encontrado'}, status=404)

# ==================== ENDPOINTS DE NÓMINA ====================
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .payroll_services import PayrollService
from .payroll_permissions import IsHROrClientAdmin, CanViewOwnPaystubs
from django.template.loader import render_to_string
from django.http import HttpResponse

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def payroll_preview(request):
    """Preview de nómina sin persistir"""
    from .payroll_calculator import get_payroll_summary
    
    gross_salary = request.data.get('gross_salary')
    is_fortnight = request.data.get('is_fortnight', True)
    
    if not gross_salary:
        return Response({'error': 'gross_salary requerido'}, status=400)
    
    try:
        gross = Decimal(str(gross_salary))
        summary = get_payroll_summary(gross, is_fortnight)
        return Response(summary)
    except Exception as e:
        return Response({'error': str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsHROrClientAdmin])
def payroll_generate(request):
    """Generar recibos de nómina para un período"""
    year = request.data.get('year')
    fortnight = request.data.get('fortnight')
    employee_ids = request.data.get('employee_ids')
    
    if not year or not fortnight:
        return Response({'error': 'year y fortnight requeridos'}, status=400)
    
    try:
        results = PayrollService.bulk_generate_for_period(
            request.user.tenant,
            int(year),
            int(fortnight),
            employee_ids
        )
        return Response(results)
    except Exception as e:
        return Response({'error': str(e)}, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_my_stubs(request):
    """Empleado lista sus recibos"""
    try:
        employee = Employee.objects.get(user=request.user)
        summaries = FortnightSummary.objects.filter(
            employee=employee,
            is_paid=True
        ).order_by('-fortnight_year', '-fortnight_number')[:12]
        
        data = [{
            'id': s.id,
            'period': s.fortnight_display,
            'gross': float(s.total_earnings),
            'deductions': float(s.total_deductions),
            'net': float(s.net_salary),
            'paid_at': s.paid_at.isoformat() if s.paid_at else None,
            'receipt_number': s.receipt.receipt_number if hasattr(s, 'receipt') else None
        } for s in summaries]
        
        return Response({'stubs': data})
    except Employee.DoesNotExist:
        return Response({'error': 'No es empleado'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def payroll_stub_download(request, stub_id):
    """Descargar PDF del recibo"""
    try:
        summary = FortnightSummary.objects.get(id=stub_id)
        
        # Verificar permisos
        if not request.user.is_superuser:
            if summary.employee.user != request.user:
                return Response({'error': 'Sin permisos'}, status=403)
        
        if not summary.is_paid:
            return Response({'error': 'Recibo no pagado'}, status=400)
        
        receipt = PaymentReceipt.objects.get(fortnight_summary=summary)
        
        # Renderizar HTML
        html = render_to_string('payroll/paystub.html', {
            'summary': summary,
            'receipt': receipt,
            'company_name': request.user.tenant.name if request.user.tenant else 'MI EMPRESA',
            'now': timezone.now()
        })
        
        # Retornar HTML (para PDF usar WeasyPrint en producción)
        response = HttpResponse(html, content_type='text/html')
        response['Content-Disposition'] = f'inline; filename="recibo_{receipt.receipt_number}.html"'
        return response
        
    except FortnightSummary.DoesNotExist:
        return Response({'error': 'Recibo no encontrado'}, status=404)

@api_view(['POST'])
@permission_classes([IsAuthenticated, IsHROrClientAdmin])
def payroll_mark_paid(request, stub_id):
    """Marcar recibo como pagado"""
    try:
        summary = FortnightSummary.objects.get(id=stub_id)
        
        if summary.is_paid:
            return Response({'error': 'Ya está pagado'}, status=400)
        
        method = request.data.get('payment_method', 'transfer')
        transaction_id = request.data.get('transaction_id', '')
        
        receipt = PayrollService.mark_paystub_as_paid(
            summary,
            timezone.now(),
            method,
            transaction_id
        )
        
        return Response({
            'success': True,
            'receipt_number': receipt.receipt_number,
            'paid_at': summary.paid_at.isoformat()
        })
        
    except FortnightSummary.DoesNotExist:
        return Response({'error': 'Recibo no encontrado'}, status=404)
