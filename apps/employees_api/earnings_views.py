from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import models
from django.db.models import Sum, Count, Q, Prefetch
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Employee
from .earnings_models import Earning, FortnightSummary
from django.core.cache import cache

class EarningViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def update_employee_config(self, request):
        """Actualizar configuración de pago de empleado"""
        try:
            employee_id = request.data.get('employee_id')
            if not employee_id:
                return Response({'error': 'employee_id requerido'}, status=400)
            
            employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
            
            # Validar payment_type
            if 'payment_type' in request.data:
                payment_type = request.data['payment_type']
                if payment_type not in ['commission', 'fixed', 'mixed']:
                    return Response({'error': 'payment_type debe ser: commission, fixed o mixed'}, status=400)
                employee.payment_type = payment_type
            
            # Validar commission_rate
            if 'commission_rate' in request.data:
                try:
                    commission_rate = float(request.data['commission_rate'])
                    if commission_rate < 0 or commission_rate > 100:
                        return Response({'error': 'commission_rate debe estar entre 0 y 100'}, status=400)
                    employee.commission_rate = commission_rate
                except (ValueError, TypeError):
                    return Response({'error': 'commission_rate debe ser un número válido'}, status=400)
            
            # Validar fixed_salary
            if 'fixed_salary' in request.data:
                try:
                    fixed_salary = float(request.data['fixed_salary'])
                    if fixed_salary < 0:
                        return Response({'error': 'fixed_salary no puede ser negativo'}, status=400)
                    employee.fixed_salary = fixed_salary
                except (ValueError, TypeError):
                    return Response({'error': 'fixed_salary debe ser un número válido'}, status=400)
            
            employee.save()
            
            return Response({
                'message': 'Configuración actualizada correctamente',
                'employee': {
                    'id': employee.id,
                    'payment_type': employee.payment_type,
                    'commission_rate': float(employee.commission_rate or 0),
                    'fixed_salary': float(employee.fixed_salary or 0)
                }
            })
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': f'Error interno: {str(e)}'}, status=500)
    
    def list(self, request):
        """Obtener ganancias reales de empleados"""
        # Obtener parámetros de filtro
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        role = request.GET.get('role')
        status_filter = request.GET.get('status')
        
        # Validación de fechas
        try:
            if start_date and end_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                if start_date > end_date:
                    return Response({'error': 'Fecha inicial no puede ser mayor a fecha final'}, status=400)
            else:
                # Fechas por defecto (quincena actual)
                today = timezone.now().date()
                if today.day <= 15:
                    start_date = today.replace(day=1)
                    end_date = today.replace(day=15)
                else:
                    start_date = today.replace(day=16)
                    last_day = (today.replace(month=today.month+1, day=1) - timedelta(days=1)).day
                    end_date = today.replace(day=last_day)
        except ValueError:
            return Response({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}, status=400)
        
        # Optimizar consulta con select_related y prefetch_related
        employees = Employee.objects.filter(
            tenant=request.user.tenant,
            is_active=True
        ).select_related('user').prefetch_related(
            Prefetch('fortnight_summaries', 
                    queryset=FortnightSummary.objects.select_related('paid_by'))
        )
        
        # Verificar si el usuario es admin y agregarlo como manager si no está en employees
        admin_employee = None
        if request.user.is_staff and not employees.filter(user=request.user).exists():
            # Crear registro temporal para el admin
            admin_employee = type('Employee', (), {
                'id': 0,
                'user': request.user,
                'specialty': 'Administrador',
                'payment_type': 'fixed',
                'commission_rate': 0,
                'fixed_salary': 0,
                'is_active': True
            })
        
        # Obtener ventas del período ACTIVO (no cerrado) para optimizar consultas
        from apps.pos_api.models import Sale
        
        # SOLO considerar ventas de períodos NO cerrados o sin período para mostrar datos pendientes correctos
        sales_data = Sale.objects.filter(
            date_time__date__gte=start_date,
            date_time__date__lte=end_date,
            employee__tenant=request.user.tenant
        ).filter(
            Q(period__isnull=True) | Q(period__closed_at__isnull=True)
        ).values('employee_id').annotate(
            total_sales=Sum('total'),
            services_count=Count('id')
        )
        
        # Crear diccionario para acceso rápido
        sales_dict = {item['employee_id']: item for item in sales_data}
        
        earnings_data = []
        all_employees = list(employees) + ([admin_employee] if admin_employee else [])
        
        for emp in all_employees:
            # Mapear specialty a role
            role_mapped = self._map_specialty_to_role(emp.specialty)
            
            # Filtrar por rol si se especifica
            if role and role_mapped != role:
                continue
            
            # Obtener datos de ventas optimizados
            if hasattr(emp, 'id') and emp.id != 0:
                employee_sales = sales_dict.get(emp.id, {'total_sales': 0, 'services_count': 0})
            else:
                # Admin temporal - no tiene ventas como empleado
                employee_sales = {'total_sales': 0, 'services_count': 0}
            
            total_sales = float(employee_sales['total_sales'] or 0)
            services_count = employee_sales['services_count'] or 0
            
            # Calcular ganancias según tipo de pago
            total_earned = self._calculate_earnings_by_type(
                emp, total_sales, start_date, end_date
            )
            
            # Determinar estado de pago (solo para empleados reales)
            if hasattr(emp, 'id') and emp.id != 0:
                payment_status = self._get_payment_status(emp, start_date, end_date, status_filter)
                # No incluir empleados sin ventas
                if payment_status == 'no_sales':
                    continue
            else:
                payment_status = 'pending'  # Admin temporal siempre pending
            
            # Para empleados con sueldo fijo, incluir aunque no tengan ventas
            if total_sales == 0 and services_count == 0 and emp.payment_type != 'fixed':
                # Solo excluir empleados sin ventas si no tienen sueldo fijo
                continue
            
            if status_filter and payment_status != status_filter:
                continue
            
            earnings_data.append({
                'id': emp.id,
                'user_id': emp.user.id,
                'full_name': emp.user.full_name or emp.user.email,
                'email': emp.user.email,
                'role': role_mapped,
                'is_active': emp.is_active,
                'payment_type': emp.payment_type or 'commission',
                'commission_rate': float(emp.commission_rate or 40),
                'fixed_salary': float(emp.fixed_salary or 0),
                'total_sales': total_sales,
                'total_earned': total_earned,
                'services_count': services_count,
                'payment_status': payment_status
            })
        
        # Calcular summary solo con datos pendientes (no cerrados)
        total_generated = sum(emp['total_sales'] for emp in earnings_data)
        total_earned_sum = sum(emp['total_earned'] for emp in earnings_data)
        
        # Para paid/pending, solo contar empleados con ventas reales
        total_paid = 0  # En este contexto, paid siempre es 0 porque solo mostramos pendientes
        total_pending = sum(emp['total_earned'] for emp in earnings_data 
                           if emp['total_sales'] > 0 or emp['services_count'] > 0)
        
        # Nueva estructura de respuesta
        return Response({
            'employees': earnings_data,
            'summary': {
                'total_generated': total_generated,
                'total_earned': total_earned_sum,
                'total_paid': total_paid,
                'total_pending': total_pending,
                'period': f"{start_date} - {end_date}",
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
        # Validar campos del empleado
        payment_type = getattr(employee, 'payment_type', 'commission') or 'commission'
        commission_rate = float(getattr(employee, 'commission_rate', 40) or 40)
        fixed_salary = float(getattr(employee, 'fixed_salary', 0) or 0)
        
        # Calcular ganancias según tipo de pago
        if payment_type == 'commission':
            total_earned = (total_sales * commission_rate) / 100
        elif payment_type == 'mixed':
            # Comisión sobre ventas
            commission_earned = (total_sales * commission_rate) / 100
            
            # Prorratear sueldo fijo por días del período
            days_in_period = (end_date - start_date).days + 1
            
            # Calcular días del mes para prorrateo
            if start_date.month == 12:
                next_month = start_date.replace(year=start_date.year + 1, month=1, day=1)
            else:
                next_month = start_date.replace(month=start_date.month + 1, day=1)
            month_days = (next_month - timedelta(days=1)).day
            
            daily_salary = fixed_salary / month_days
            prorated_salary = daily_salary * days_in_period
            total_earned = prorated_salary + commission_earned
        else:  # fixed
            # Prorratear sueldo fijo por días del período
            days_in_period = (end_date - start_date).days + 1
            
            if start_date.month == 12:
                next_month = start_date.replace(year=start_date.year + 1, month=1, day=1)
            else:
                next_month = start_date.replace(month=start_date.month + 1, day=1)
            month_days = (next_month - timedelta(days=1)).day
            
            daily_salary = fixed_salary / month_days
            total_earned = daily_salary * days_in_period
        
        return float(total_earned)
    
    def _get_payment_status(self, employee, start_date, end_date, status_filter):
        """Obtiene el estado de pago del empleado para el período"""
        from apps.pos_api.models import Sale
        
        # Verificar si hay ventas PENDIENTES (no cerradas) en el período
        pending_sales = Sale.objects.filter(
            employee=employee,
            date_time__date__gte=start_date,
            date_time__date__lte=end_date
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
            period__closed_at__isnull=False,
            period__is_paid=True
        ).exists()
        
        if paid_sales:
            return 'paid'
        
        # Si no hay ventas en el período, no mostrar el empleado
        return 'no_sales'
    
    def _calculate_fortnight_number(self, date):
        """Calcula el número de quincena (1-24)"""
        month = date.month
        day = date.day
        fortnight_in_month = 1 if day <= 15 else 2
        return (month - 1) * 2 + fortnight_in_month
    
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
                date_time__date__lte=end_date
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
                period__isnull=True
            ).update(period=summary)
            
            Sale.objects.filter(
                employee_id=employee.id,
                date_time__date__gte=start_date,
                date_time__date__lte=end_date,
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
                    'paid_by': summary.paid_by.full_name if summary.paid_by else None,
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
                date_time__date__lte=end_date
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
            employee__tenant=request.user.tenant
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