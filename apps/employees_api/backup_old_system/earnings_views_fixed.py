from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
from .models import Employee
from .earnings_models import FortnightSummary, PaymentReceipt

class EarningViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Obtener ganancias de empleados - ENDPOINT PRINCIPAL"""
        # Obtener parámetros de filtro
        start_date = request.GET.get('start_date')
        end_date = request.GET.get('end_date')
        role = request.GET.get('role')
        status_filter = request.GET.get('status')
        
        # Validación de fechas y cálculo de quincena
        try:
            if start_date and end_date:
                start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                if start_date > end_date:
                    return Response({'error': 'Fecha inicial no puede ser mayor a fecha final'}, status=400)
            else:
                # Calcular quincena actual correctamente
                today = timezone.now().date()
                start_date, end_date = self._calculate_current_fortnight(today)
        except ValueError:
            return Response({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}, status=400)
        
        # Validar tenant
        if not request.user.tenant and not request.user.is_superuser:
            return Response({'error': 'Usuario sin tenant asignado'}, status=400)
        
        # Obtener empleados del tenant
        employees_query = Employee.objects.filter(is_active=True).select_related('user')
        if not request.user.is_superuser:
            employees_query = employees_query.filter(tenant=request.user.tenant)
        
        employees = list(employees_query)
        
        # Obtener ventas COMPLETADAS del período
        from apps.pos_api.models import Sale
        
        sales_filter = {
            'date_time__date__gte': start_date,
            'date_time__date__lte': end_date,
            'status': 'completed'
        }
        
        if not request.user.is_superuser:
            sales_filter['employee__tenant'] = request.user.tenant
        
        # Obtener datos reales de ventas por empleado
        sales_data = Sale.objects.filter(**sales_filter).values('employee_id').annotate(
            total_generated=Sum('total'),
            services_count=Count('id')
        )
        
        # Crear diccionario para acceso rápido
        sales_dict = {item['employee_id']: item for item in sales_data if item['employee_id']}
        
        earnings_data = []
        
        for emp in employees:
            # Mapear specialty a role
            role_mapped = self._map_specialty_to_role(emp.specialty)
            
            # Filtrar por rol si se especifica
            if role and role_mapped != role:
                continue
            
            # Obtener datos reales de ventas del empleado
            employee_sales = sales_dict.get(emp.id, {'total_generated': 0, 'services_count': 0})
            total_generated = float(employee_sales['total_generated'] or 0)
            services_count = employee_sales['services_count'] or 0
            
            # Calcular ganancias según tipo de pago real
            total_earned = self._calculate_real_earnings(
                emp, total_generated, services_count, start_date, end_date
            )
            
            # Determinar estado de pago
            payment_status = self._get_real_payment_status(emp, start_date, end_date)
            
            # Aplicar filtros
            if status_filter and payment_status != status_filter:
                continue
            
            # Solo incluir empleados con actividad o sueldo fijo
            if total_generated == 0 and services_count == 0 and emp.salary_type != 'fixed':
                continue
            
            earnings_data.append({
                'id': emp.id,
                'user_id': emp.user.id,
                'full_name': emp.user.full_name or emp.user.email,
                'email': emp.user.email,
                'role': role_mapped,
                'is_active': emp.is_active,
                'payment_type': emp.salary_type,
                'commission_rate': float(emp.commission_percentage or 40),
                'fixed_salary': float(emp.salary_amount or 0),
                'total_sales': total_generated,
                'total_earned': total_earned,
                'services_count': services_count,
                'payment_status': payment_status
            })
        
        # Calcular resumen real
        total_generated = sum(emp['total_sales'] for emp in earnings_data)
        total_earned_sum = sum(emp['total_earned'] for emp in earnings_data)
        total_paid = sum(emp['total_earned'] for emp in earnings_data if emp['payment_status'] == 'paid')
        total_pending = sum(emp['total_earned'] for emp in earnings_data if emp['payment_status'] == 'pending')
        
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
    
    @action(detail=False, methods=['post'])
    def pay(self, request):
        """Procesar pago de empleado - ENDPOINT PARA FRONTEND"""
        employee_id = request.data.get('employee_id')
        period_start = request.data.get('period_start')
        period_end = request.data.get('period_end')
        payment_method = request.data.get('payment_method', 'cash')
        payment_reference = request.data.get('payment_reference', '')
        payment_notes = request.data.get('payment_notes', '')
        
        if not employee_id:
            return Response({'error': 'employee_id es requerido'}, status=400)
        if not period_start or not period_end:
            return Response({'error': 'period_start y period_end son requeridos'}, status=400)
        
        try:
            # Validar empleado y tenant
            employee_filter = {'id': employee_id}
            if not request.user.is_superuser:
                employee_filter['tenant'] = request.user.tenant
            
            employee = Employee.objects.get(**employee_filter)
            
            # Validar fechas
            start_date = datetime.strptime(period_start, '%Y-%m-%d').date()
            end_date = datetime.strptime(period_end, '%Y-%m-%d').date()
            
            # Validar que es una quincena válida
            if not self._is_valid_fortnight(start_date, end_date):
                return Response({'error': 'El período debe ser una quincena válida (1-15 o 16-fin de mes)'}, status=400)
            
            # Calcular datos de la quincena
            year = start_date.year
            month = start_date.month
            fortnight_in_month = 1 if start_date.day <= 15 else 2
            fortnight_number = (month - 1) * 2 + fortnight_in_month
            
            # Obtener ventas completadas del período
            from apps.pos_api.models import Sale
            sales_filter = {
                'employee': employee,
                'date_time__date__gte': start_date,
                'date_time__date__lte': end_date,
                'status': 'completed'
            }
            
            sales_data = Sale.objects.filter(**sales_filter).aggregate(
                total_generated=Sum('total'),
                services_count=Count('id')
            )
            
            total_generated = float(sales_data['total_generated'] or 0)
            services_count = sales_data['services_count'] or 0
            
            # Calcular ganancias según tipo de pago
            total_earned = self._calculate_real_earnings(
                employee, total_generated, services_count, start_date, end_date
            )
            
            # Validar que hay algo que pagar
            if total_earned <= 0:
                return Response({'error': 'No hay ganancias que pagar en este período'}, status=400)
            
            # Crear o actualizar FortnightSummary
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
                    'closed_at': timezone.now(),
                    'payment_method': payment_method,
                    'amount_paid': total_earned,
                    'payment_reference': payment_reference,
                    'payment_notes': payment_notes
                }
            )
            
            if not created:
                if summary.is_paid and summary.closed_at:
                    return Response({'error': 'Este período ya fue pagado y cerrado'}, status=400)
                
                # Actualizar resumen existente
                summary.total_earnings = total_earned
                summary.total_services = services_count
                summary.is_paid = True
                summary.paid_at = timezone.now()
                summary.paid_by = request.user
                summary.closed_at = timezone.now()
                summary.payment_method = payment_method
                summary.amount_paid = total_earned
                summary.payment_reference = payment_reference
                summary.payment_notes = payment_notes
                summary.save()
            
            # Asignar ventas al período
            Sale.objects.filter(**sales_filter).update(period=summary)
            
            # Generar recibo
            receipt, receipt_created = PaymentReceipt.objects.get_or_create(
                fortnight_summary=summary
            )
            
            return Response({
                'status': 'paid',
                'message': 'Pago procesado correctamente',
                'summary': {
                    'period_id': summary.id,
                    'fortnight_display': summary.fortnight_display,
                    'total_generated': total_generated,
                    'total_earned': float(summary.total_earnings),
                    'services_count': summary.total_services,
                    'payment_type': employee.salary_type,
                    'payment_method': summary.payment_method,
                    'payment_reference': summary.payment_reference,
                    'receipt_number': receipt.receipt_number,
                    'paid_at': summary.paid_at.isoformat()
                }
            })
            
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
        except ValueError:
            return Response({'error': 'Formato de fecha inválido. Use YYYY-MM-DD'}, status=400)
        except Exception as e:
            return Response({'error': f'Error interno: {str(e)}'}, status=500)
    
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
            
            # Validar salary_amount (fixed_salary)
            if 'fixed_salary' in request.data or 'salary_amount' in request.data:
                try:
                    salary_amount = float(
                        request.data.get('salary_amount') or request.data.get('fixed_salary')
                    )
                    if salary_amount < 0:
                        return Response({'error': 'salary_amount no puede ser negativo'}, status=400)
                    employee.salary_amount = salary_amount
                except (ValueError, TypeError):
                    return Response({'error': 'salary_amount debe ser un número válido'}, status=400)
            
            employee.save()
            
            return Response({
                'message': 'Configuración actualizada correctamente',
                'employee': {
                    'id': employee.id,
                    'salary_type': employee.salary_type,
                    'commission_percentage': float(employee.commission_percentage or 0),
                    'salary_amount': float(employee.salary_amount or 0),
                    # Compatibilidad con nombres anteriores
                    'payment_type': employee.salary_type,
                    'commission_rate': float(employee.commission_percentage or 0),
                    'fixed_salary': float(employee.salary_amount or 0)
                }
            })
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': f'Error interno: {str(e)}'}, status=500)
    
    # MÉTODOS HELPER
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
    
    def _calculate_current_fortnight(self, date):
        """Calcula las fechas exactas de la quincena actual"""
        if date.day <= 15:
            # Primera quincena: día 1 al 15
            start_date = date.replace(day=1)
            end_date = date.replace(day=15)
        else:
            # Segunda quincena: día 16 al último día del mes
            start_date = date.replace(day=16)
            # Calcular último día del mes
            if date.month == 12:
                next_month = date.replace(year=date.year + 1, month=1, day=1)
            else:
                next_month = date.replace(month=date.month + 1, day=1)
            last_day = (next_month - timedelta(days=1)).day
            end_date = date.replace(day=last_day)
        
        return start_date, end_date
    
    def _calculate_real_earnings(self, employee, total_generated, services_count, start_date, end_date):
        """Calcula ganancias reales según el flujo de negocio"""
        salary_type = employee.salary_type or 'commission'
        commission_percentage = float(employee.commission_percentage or 40)
        salary_amount = float(employee.salary_amount or 0)
        
        if salary_type == 'commission':
            # Solo comisión: porcentaje del total generado
            return (total_generated * commission_percentage) / 100
        
        elif salary_type == 'fixed':
            # Solo sueldo fijo: monto quincenal completo
            return salary_amount
        
        elif salary_type == 'mixed':
            # Mixto: sueldo base + comisión
            commission_earned = (total_generated * commission_percentage) / 100
            return salary_amount + commission_earned
        
        return 0.0
    
    def _get_real_payment_status(self, employee, start_date, end_date):
        """Determina el estado real de pago según FortnightSummary"""
        # Calcular número de quincena
        year = start_date.year
        month = start_date.month
        fortnight_in_month = 1 if start_date.day <= 15 else 2
        fortnight_number = (month - 1) * 2 + fortnight_in_month
        
        # Buscar resumen de quincena existente
        try:
            summary = FortnightSummary.objects.get(
                employee=employee,
                fortnight_year=year,
                fortnight_number=fortnight_number
            )
            return 'paid' if summary.is_paid else 'pending'
        except FortnightSummary.DoesNotExist:
            # No existe resumen, verificar si hay ventas en el período o sueldo fijo
            from apps.pos_api.models import Sale
            has_sales = Sale.objects.filter(
                employee=employee,
                date_time__date__gte=start_date,
                date_time__date__lte=end_date,
                status='completed'
            ).exists()
            
            # Si es sueldo fijo, siempre hay algo que pagar
            if employee.salary_type == 'fixed':
                return 'pending'
            
            return 'pending' if has_sales else 'no_sales'
    
    def _is_valid_fortnight(self, start_date, end_date):
        """Valida que las fechas correspondan a una quincena válida"""
        # Primera quincena: 1-15
        if start_date.day == 1 and end_date.day == 15:
            return start_date.month == end_date.month and start_date.year == end_date.year
        
        # Segunda quincena: 16-fin de mes
        if start_date.day == 16:
            # Calcular último día del mes
            if start_date.month == 12:
                next_month = start_date.replace(year=start_date.year + 1, month=1, day=1)
            else:
                next_month = start_date.replace(month=start_date.month + 1, day=1)
            last_day = (next_month - timedelta(days=1)).day
            
            return (end_date.day == last_day and 
                   start_date.month == end_date.month and 
                   start_date.year == end_date.year)
        
        return False