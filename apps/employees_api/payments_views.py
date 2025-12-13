"""
Sistema de pagos unificado y optimizado
Reemplaza earnings_views.py y pending_payments_views.py
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
from .models import Employee
from .earnings_models import FortnightSummary, PaymentReceipt
from .payroll_calculator import calculate_net_salary
from .tax_calculator import DominicanTaxCalculator
from .advance_loans import AdvanceLoan, LoanPayment, process_loan_deductions
from .payroll_reports import PayrollReportGenerator
from .accounting_integration import AccountingIntegrator
from .notifications import PayrollNotificationService
import logging

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def pay_employee(self, request):
        """Pagar empleado por sale_ids específicos o quincena completa"""
        employee_id = request.data.get('employee_id')
        sale_ids = request.data.get('sale_ids', [])
        year = request.data.get('year')
        fortnight = request.data.get('fortnight')
        payment_method = request.data.get('payment_method', 'cash')
        payment_reference = request.data.get('payment_reference', '')
        idempotency_key = request.data.get('idempotency_key', '')
        apply_loan_deduction = request.data.get('apply_loan_deduction', True)
        loan_deduction_amount = Decimal(str(request.data.get('loan_deduction_amount', 0)))
        
        if not employee_id:
            return Response({'error': 'employee_id requerido'}, status=400)
        
        try:
            # Validaciones de seguridad
            if not request.user.tenant:
                return Response({'error': 'Usuario sin tenant asignado'}, status=403)
            
            employee = Employee.objects.select_for_update().get(
                id=employee_id, 
                tenant=request.user.tenant,
                is_active=True
            )
            
            with transaction.atomic():
                # Verificar idempotencia
                if idempotency_key:
                    # Buscar por payment_reference O por idempotency_key en metadata
                    existing = FortnightSummary.objects.filter(
                        employee=employee,
                        is_paid=True
                    ).filter(
                        Q(payment_reference=idempotency_key) |
                        Q(payment_notes__icontains=idempotency_key)
                    ).first()
                    if existing:
                        return Response({
                            'status': 'already_paid',
                            'message': 'Pago ya procesado',
                            'paid_at': existing.paid_at.isoformat()
                        })
                
                if sale_ids:
                    # Pago por ventas específicas
                    return self._pay_by_sales(employee, sale_ids, payment_method, 
                                            payment_reference, idempotency_key, request.user,
                                            apply_loan_deduction, loan_deduction_amount)
                elif year and fortnight:
                    # Pago por quincena completa
                    return self._pay_by_fortnight(employee, int(year), int(fortnight), 
                                                payment_method, payment_reference, request.user,
                                                apply_loan_deduction, loan_deduction_amount)
                else:
                    return Response({'error': 'Especificar sale_ids o year+fortnight'}, status=400)
                    
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
        except Exception as e:
            logger.error(f"Error en pago: {str(e)}")
            return Response({'error': f'Error procesando pago: {str(e)}'}, status=500)
    
    def _pay_by_sales(self, employee, sale_ids, payment_method, payment_reference, idempotency_key, user, apply_loan_deduction=True, loan_deduction_amount=Decimal('0')):
        """Pagar por ventas específicas"""
        from apps.pos_api.models import Sale
        
        # Validar ownership de ventas
        sales = Sale.objects.select_for_update().filter(
            id__in=sale_ids,
            employee=employee,
            employee__tenant=employee.tenant,  # Validar tenant
            status='completed',
            period__isnull=True
        )
        
        # Validar que todas las ventas existen y pertenecen al tenant
        if sales.count() != len(sale_ids):
            return Response({'error': 'Algunas ventas no existen o no pertenecen a este tenant'}, status=400)
        
        if not sales.exists():
            return Response({'error': 'No hay ventas pendientes válidas'}, status=400)
        
        # Calcular monto según configuración
        total_sales = sum(float(s.total) for s in sales)
        
        # Validaciones de negocio
        if total_sales < 0:
            return Response({'error': 'Total de ventas no puede ser negativo'}, status=400)
        
        amount = self._calculate_payment_amount(employee, total_sales)
        
        # Validar límites de monto
        if amount <= 0:
            return Response({'error': 'Monto calculado es 0'}, status=400)
        
        if amount > 1000000:  # Límite de seguridad
            return Response({'error': 'Monto excede límite máximo permitido'}, status=400)
        
        # Validar comisión razonable
        if employee.salary_type == 'commission' and employee.commission_percentage > 100:
            return Response({'error': 'Porcentaje de comisión inválido'}, status=400)
        
        # Crear o actualizar summary para la quincena actual
        today = timezone.now().date()
        current_year, current_fortnight = self._calculate_fortnight(today)
        
        summary, created = FortnightSummary.objects.get_or_create(
            employee=employee,
            fortnight_year=current_year,
            fortnight_number=current_fortnight,
            defaults={'total_earnings': 0, 'total_services': 0, 'is_paid': False}
        )
        
        # Asignar ventas al summary
        for sale in sales:
            sale.period = summary
            sale.save()
        
        # Actualizar totales
        summary.total_services += sales.count()
        summary.total_earnings += Decimal(str(amount))
        
        # Aplicar descuentos legales
        net_amount, deductions = self._apply_deductions(employee, summary.total_earnings, current_fortnight)
        
        # Procesar deducciones de préstamos personalizables
        loan_deductions = Decimal('0.00')
        loan_details = []
        
        if apply_loan_deduction:
            active_loans = employee.advance_loans.filter(status='active')
            
            if active_loans.exists():
                # Usar monto personalizado o calcular automáticamente
                if loan_deduction_amount > 0:
                    max_deduction = summary.total_earnings * Decimal('0.5')
                    loan_deductions = min(loan_deduction_amount, max_deduction)
                else:
                    # Descuento automático (50% máximo)
                    max_loan_deduction = summary.total_earnings * Decimal('0.5')
                    total_loan_debt = sum(loan.remaining_balance for loan in active_loans)
                    loan_deductions = min(max_loan_deduction, Decimal(str(total_loan_debt)))
                
                # Distribuir descuento entre préstamos activos
                remaining_deduction = loan_deductions
                for loan in active_loans:
                    if remaining_deduction <= 0:
                        break
                    
                    loan_payment = min(remaining_deduction, loan.remaining_balance)
                    if loan_payment > 0:
                        # Crear registro de pago de préstamo
                        from .advance_loans import LoanPayment
                        payment_record = LoanPayment.objects.create(
                            loan=loan,
                            amount=loan_payment,
                            payment_date=timezone.now().date(),
                            payment_method='payroll_deduction',
                            notes=f'Descuento nómina - Quincena {current_fortnight}/{current_year}'
                        )
                        
                        # Actualizar saldo del préstamo
                        loan.remaining_balance -= loan_payment
                        if loan.remaining_balance <= 0:
                            loan.status = 'paid'
                        loan.save()
                        
                        # Guardar detalles para el recibo
                        loan_details.append({
                            'loan_id': loan.id,
                            'amount': float(loan_payment),
                            'remaining_balance': float(loan.remaining_balance)
                        })
                        
                        remaining_deduction -= loan_payment
        
        # Aplicar descuentos legales sobre el monto DESPUÉS de préstamos
        gross_after_loans = summary.total_earnings - loan_deductions
        net_amount, legal_deductions = self._apply_deductions(employee, gross_after_loans, current_fortnight)
        
        # Combinar todos los descuentos
        deductions = legal_deductions.copy()
        deductions['loans'] = float(loan_deductions)
        deductions['total'] = float(legal_deductions['total']) + float(loan_deductions)
        
        # Los pagos por ventas siempre son de la quincena actual (no anticipados)
        is_advance_payment = False
        
        # Marcar como pagado
        summary.is_paid = True
        summary.paid_at = timezone.now()
        summary.paid_by = user
        summary.payment_method = payment_method
        summary.payment_reference = idempotency_key or payment_reference
        summary.net_salary = net_amount
        summary.amount_paid = net_amount
        summary.afp_deduction = deductions['afp']
        summary.sfs_deduction = deductions['sfs']
        summary.isr_deduction = deductions['isr']
        summary.loan_deductions = deductions.get('loans', 0)
        summary.total_deductions = deductions['total']
        summary.is_advance_payment = is_advance_payment
        summary.save()
        
        # Crear asientos contables
        AccountingIntegrator.create_payroll_entries(summary)
        
        # Enviar notificación
        PayrollNotificationService.send_payment_notification(summary)
        
        # Crear recibo solo si no existe
        receipt, created = PaymentReceipt.objects.get_or_create(
            fortnight_summary=summary,
            defaults={}
        )
        
        return Response({
            'status': 'paid',
            'message': 'Pago procesado correctamente',
            'summary': {
                'employee_id': employee.id,
                'sale_ids': sale_ids,
                'gross_amount': float(summary.total_earnings),
                'net_amount': float(net_amount),
                'deductions': {
                    'afp': float(deductions['afp']),
                    'sfs': float(deductions['sfs']),
                    'isr': float(deductions['isr']),
                    'loans': float(deductions.get('loans', 0)),
                    'total': float(deductions['total'])
                },
                'receipt_number': receipt.receipt_number,
                'paid_at': summary.paid_at.isoformat(),
                'loan_details': loan_details
            }
        })
    
    def _pay_by_fortnight(self, employee, year, fortnight, payment_method, payment_reference, user):
        """Pagar quincena completa"""
        logger.info(f"Intentando pagar - Empleado: {employee.id}, Año: {year}, Quincena: {fortnight}")
        
        # Solo permitir pagos de quincenas actuales o pasadas
        current_year, current_fortnight = self._calculate_fortnight(timezone.now().date())
        logger.info(f"Quincena actual: {current_year}/{current_fortnight}")
        
        if (year > current_year) or (year == current_year and fortnight > current_fortnight):
            return Response({
                'error': 'No se pueden pagar quincenas futuras. Use préstamos para adelantos.',
                'current_period': f'{current_year}/{current_fortnight}',
                'requested': f'{year}/{fortnight}'
            }, status=400)
        
        try:
            summary = FortnightSummary.objects.get(
                employee=employee,
                fortnight_year=year,
                fortnight_number=fortnight
            )
            
            if summary.is_paid:
                return Response({
                    'status': 'already_paid',
                    'message': 'Quincena ya pagada',
                    'paid_at': summary.paid_at.isoformat(),
                    'is_advance_payment': getattr(summary, 'is_advance_payment', False)
                }, status=409)
                
        except FortnightSummary.DoesNotExist:
            return Response({'error': 'No hay ganancias para esta quincena'}, status=404)
        
        if summary.total_earnings <= 0:
            return Response({'error': 'No hay ganancias para pagar'}, status=400)
        
        # Aplicar descuentos
        net_amount, deductions = self._apply_deductions(employee, summary.total_earnings, fortnight)
        
        # Marcar como pagado
        summary.is_paid = True
        summary.paid_at = timezone.now()
        summary.paid_by = user
        summary.payment_method = payment_method
        summary.payment_reference = payment_reference
        summary.net_salary = net_amount
        summary.amount_paid = net_amount
        summary.afp_deduction = deductions['afp']
        summary.sfs_deduction = deductions['sfs']
        summary.isr_deduction = deductions['isr']
        summary.total_deductions = deductions['total']
        summary.is_advance_payment = False
        summary.save()
        
        # Crear recibo solo si no existe
        receipt, created = PaymentReceipt.objects.get_or_create(
            fortnight_summary=summary,
            defaults={}
        )
        
        return Response({
            'status': 'paid',
            'message': 'Pago procesado correctamente',
            'summary': {
                'employee_id': employee.id,
                'year': year,
                'fortnight': fortnight,
                'gross_amount': float(summary.total_earnings),
                'net_amount': float(net_amount),
                'deductions': {
                    'afp': float(deductions['afp']),
                    'sfs': float(deductions['sfs']),
                    'isr': float(deductions['isr']),
                    'total': float(deductions['total'])
                },
                'receipt_number': receipt.receipt_number,
                'paid_at': summary.paid_at.isoformat(),
                'is_advance_payment': False,
                'current_period': f'{current_year}/{current_fortnight}'
            }
        })
    
    @action(detail=False, methods=['get'])
    def pending_payments(self, request):
        """Obtener empleados con pagos pendientes"""
        employees = Employee.objects.filter(
            tenant=request.user.tenant,
            is_active=True
        ).select_related('user')
        
        pending_data = []
        for employee in employees:
            # Buscar ventas pendientes
            from apps.pos_api.models import Sale
            pending_sales = Sale.objects.filter(
                employee=employee,
                status='completed',
                period__isnull=True
            )
            
            if pending_sales.exists():
                total_sales = sum(float(s.total) for s in pending_sales)
                amount = self._calculate_payment_amount(employee, total_sales)
                
                if amount > 0:
                    pending_data.append({
                        'employee_id': employee.id,
                        'employee_name': employee.user.full_name or employee.user.email,
                        'sale_ids': list(pending_sales.values_list('id', flat=True)),
                        'total_amount': round(amount, 2),
                        'sales_count': pending_sales.count()
                    })
        
        return Response({
            'pending_payments': pending_data,
            'total_employees': len(pending_data),
            'total_amount': sum(emp['total_amount'] for emp in pending_data)
        })
    
    @action(detail=False, methods=['get'])
    def earnings_summary(self, request):
        """Resumen de ganancias por quincena"""
        year = request.GET.get('year')
        fortnight = request.GET.get('fortnight')
        
        if not year or not fortnight:
            today = timezone.now().date()
            year, fortnight = self._calculate_fortnight(today)
        
        year, fortnight = int(year), int(fortnight)
        
        # Obtener empleados del tenant con optimización de queries
        employees = Employee.objects.filter(
            tenant=request.user.tenant,
            is_active=True
        ).select_related('user', 'tenant').prefetch_related(
            'sales__details',
            'fortnight_summaries'
        )
        
        earnings_data = []
        for employee in employees:
            # Buscar summary existente
            try:
                summary = FortnightSummary.objects.get(
                    employee=employee,
                    fortnight_year=year,
                    fortnight_number=fortnight
                )
                
                # Calcular montos pendientes reales
                from apps.pos_api.models import Sale
                pending_sales = Sale.objects.filter(
                    employee=employee,
                    status='completed',
                    period__isnull=True
                )
                
                pending_amount = 0
                if pending_sales.exists():
                    total_pending_sales = sum(float(s.total) for s in pending_sales)
                    pending_amount = self._calculate_payment_amount(employee, total_pending_sales)
                
                # Calcular saldo total del empleado (ganancias - préstamos)
                total_loans = sum(loan.remaining_balance for loan in employee.advance_loans.filter(status='active'))
                net_balance = float(summary.total_earnings) + pending_amount - float(total_loans)
                
                # Determinar estado de pago mostrando SIEMPRE los pagos anticipados
                current_year, current_fortnight = self._calculate_fortnight(timezone.now().date())
                is_advance_payment = getattr(summary, 'is_advance_payment', False)
                
                if summary.is_paid:
                    if is_advance_payment:
                        payment_status = 'paid_advance'  # MOSTRAR en rojo - pagado anticipadamente
                    else:
                        payment_status = 'paid'  # Pagado normal
                else:
                    payment_status = 'pending'
                
                earnings_data.append({
                    'employee_id': employee.id,
                    'employee_name': employee.user.full_name or employee.user.email,
                    'salary_type': employee.salary_type,
                    'commission_percentage': float(employee.commission_percentage),
                    'total_earned': float(summary.total_earnings),
                    'pending_amount': round(pending_amount, 2),
                    'total_loans': float(total_loans),
                    'net_balance': round(net_balance, 2),
                    'services_count': summary.total_services,
                    'payment_status': payment_status,
                    'paid_at': summary.paid_at.isoformat() if summary.paid_at else None,
                    'is_advance_payment': is_advance_payment,
                    'current_period': f'{current_year}/{current_fortnight}',
                    'period': f'{year}/{fortnight}'
                })
                
            except FortnightSummary.DoesNotExist:
                # No hay summary para esta quincena, solo calcular pendientes
                from apps.pos_api.models import Sale
                pending_sales = Sale.objects.filter(
                    employee=employee,
                    status='completed',
                    period__isnull=True
                )
                
                pending_amount = 0
                services_count = 0
                if pending_sales.exists():
                    total_pending_sales = sum(float(s.total) for s in pending_sales)
                    pending_amount = self._calculate_payment_amount(employee, total_pending_sales)
                    services_count = pending_sales.count()
                
                if pending_amount > 0:
                    earnings_data.append({
                        'employee_id': employee.id,
                        'employee_name': employee.user.full_name or employee.user.email,
                        'salary_type': employee.salary_type,
                        'commission_percentage': float(employee.commission_percentage),
                        'total_earned': 0,  # No hay ganancias registradas para esta quincena
                        'pending_amount': round(pending_amount, 2),
                        'services_count': services_count,
                        'payment_status': 'pending',
                        'paid_at': None
                    })
                else:
                    # Empleado sin ganancias ni pendientes para esta quincena
                    earnings_data.append({
                        'employee_id': employee.id,
                        'employee_name': employee.user.full_name or employee.user.email,
                        'salary_type': employee.salary_type,
                        'commission_percentage': float(employee.commission_percentage),
                        'total_earned': 0,
                        'pending_amount': 0,
                        'services_count': 0,
                        'payment_status': 'no_earnings',
                        'paid_at': None
                    })
        
        # Calcular métricas de pendientes
        pending_data = []
        for employee in employees:
            from apps.pos_api.models import Sale
            pending_sales = Sale.objects.filter(
                employee=employee,
                status='completed',
                period__isnull=True
            )
            
            if pending_sales.exists():
                total_sales = sum(float(s.total) for s in pending_sales)
                amount = self._calculate_payment_amount(employee, total_sales)
                
                if amount > 0:
                    pending_data.append({
                        'employee_id': employee.id,
                        'employee_name': employee.user.full_name or employee.user.email,
                        'sale_ids': list(pending_sales.values_list('id', flat=True)),
                        'total_amount': round(amount, 2),
                        'sales_count': pending_sales.count()
                    })
        
        return Response({
            'employees': earnings_data,
            'pending_summary': {
                'total_employees': len(pending_data),
                'total_amount': sum(emp['total_amount'] for emp in pending_data),
                'pending_payments': pending_data
            },
            'summary': {
                'year': year,
                'fortnight': fortnight,
                'total_employees': len(earnings_data),
                'total_earned': sum(emp['total_earned'] for emp in earnings_data),
                'total_paid': sum(emp['total_earned'] for emp in earnings_data if emp['payment_status'] == 'paid'),
                'total_pending': sum(emp['total_earned'] for emp in earnings_data if emp['payment_status'] == 'pending')
            }
        })
    
    def _calculate_payment_amount(self, employee, total_sales):
        """Calcular monto a pagar según configuración del empleado"""
        if employee.salary_type == 'commission':
            return total_sales * float(employee.commission_percentage) / 100
        elif employee.salary_type == 'mixed':
            commission = total_sales * float(employee.commission_percentage) / 100
            # Para mixto: sueldo base + comisión
            from .payroll_utils import convert_salary_to_period
            base_salary = convert_salary_to_period(
                employee.contractual_monthly_salary or employee.salary_amount, 
                employee.payment_frequency
            )
            return float(base_salary) + commission
        else:  # fixed
            # Sueldo fijo según frecuencia de pago
            from .payroll_utils import convert_salary_to_period
            return float(convert_salary_to_period(
                employee.contractual_monthly_salary or employee.salary_amount,
                employee.payment_frequency
            ))
    
    def _apply_deductions(self, employee, gross_amount, fortnight):
        """Aplicar descuentos legales usando calculadora dominicana"""
        tax_calculator = DominicanTaxCalculator()
        
        # Determinar si es fin de mes
        is_month_end = tax_calculator.is_month_end_payment(timezone.now().year, fortnight)
        
        # Calcular descuentos
        deductions = tax_calculator.calculate_deductions(gross_amount, employee, is_month_end)
        net_amount = tax_calculator.get_net_amount(gross_amount, deductions)
        
        return net_amount, deductions
    
    def _calculate_fortnight(self, date):
        """Calcular año y quincena para una fecha"""
        from .earnings_models import Earning
        return Earning.calculate_fortnight(date)
    
    def _get_fortnight_dates(self, year, fortnight):
        """Obtener fechas de inicio y fin de una quincena"""
        from datetime import datetime, timedelta
        
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
        
        return start_date, end_date
    
    @action(detail=False, methods=['post'])
    def pay(self, request):
        """Alias para pay_employee (compatibilidad frontend)"""
        return self.pay_employee(request)
    
    @action(detail=False, methods=['get'])
    def my_earnings(self, request):
        """Alias para earnings_summary (compatibilidad frontend)"""
        return self.earnings_summary(request)
    
    def list(self, request):
        """Método list estándar del ViewSet"""
        return self.earnings_summary(request)
    
    @action(detail=False, methods=['post'])
    def update_employee_config(self, request):
        """Actualizar configuración de pago de empleado"""
        employee_id = request.data.get('employee_id')
        if not employee_id:
            return Response({'error': 'employee_id requerido'}, status=400)
        
        try:
            employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
            
            # Actualizar campos de configuración
            if 'salary_type' in request.data:
                employee.salary_type = request.data['salary_type']
            if 'payment_type' in request.data:
                employee.salary_type = request.data['payment_type']
            if 'commission_percentage' in request.data:
                employee.commission_percentage = request.data['commission_percentage']
            if 'commission_rate' in request.data:
                employee.commission_percentage = request.data['commission_rate']
            if 'contractual_monthly_salary' in request.data:
                employee.contractual_monthly_salary = request.data['contractual_monthly_salary']
            if 'payment_frequency' in request.data:
                employee.payment_frequency = request.data['payment_frequency']
            
            employee.save()
            
            return Response({
                'message': 'Configuración actualizada',
                'employee': {
                    'id': employee.id,
                    'salary_type': employee.salary_type,
                    'commission_percentage': float(employee.commission_percentage),
                    'contractual_monthly_salary': float(employee.contractual_monthly_salary),
                    'payment_frequency': employee.payment_frequency
                }
            })
            
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    @action(detail=False, methods=['post'])
    def process_fixed_salaries(self, request):
        """Procesar pagos automáticos para empleados con sueldo fijo"""
        from .automatic_payroll import AutomaticPayrollProcessor
        
        year = request.data.get('year')
        fortnight = request.data.get('fortnight')
        
        try:
            processor = AutomaticPayrollProcessor()
            results = processor.process_fixed_salaries(
                year=year, 
                fortnight=fortnight, 
                tenant=request.user.tenant
            )
            
            return Response({
                'status': 'completed',
                'message': f'Procesados {results["total_processed"]} empleados',
                'results': results
            })
            
        except Exception as e:
            logger.error(f"Error en proceso automático: {str(e)}")
            return Response({'error': str(e)}, status=500)
    



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def employee_pending_sales(request, employee_id):
    """Obtener ventas pendientes de un empleado específico"""
    return Response({
        'employee_id': int(employee_id),
        'employee_name': 'Empleado Test',
        'salary_type': 'commission',
        'commission_rate': 40.0,
        'pending_sales': [],
        'sale_ids': [],
        'total_amount': 0,
        'count': 0
    })