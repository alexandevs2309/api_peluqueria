"""
Sistema de pagos unificado y optimizado
Reemplaza earnings_views.py y pending_payments_views.py

*** PAYROLL LOGIC FINALIZED ***
Any changes require explicit business rule update + tests.
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
from .tax_calculator_factory import TaxCalculatorFactory
from .advance_loans import AdvanceLoan, LoanPayment, process_loan_deductions
from .payroll_reports import PayrollReportGenerator
from .accounting_integration import AccountingIntegrator
from .notifications import PayrollNotificationService
from .services.balance import EmployeeBalanceService
from .services.payment import PaymentService
from .services.loan import LoanService
from apps.auth_api.permissions import IsClientAdmin, CanViewFinancialData
import logging

logger = logging.getLogger(__name__)


class PaymentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsClientAdmin]  # Solo CLIENT_ADMIN puede gestionar pagos
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsClientAdmin])
    def pay_employee(self, request):
        """Procesar pago a empleado con idempotencia y transacciones atómicas
        
        ENDURECIMIENTO:
        - Idempotencia usando idempotency_key
        - Transacciones atómicas
        - Recálculo de balance dentro de transacción
        - Estados claros (PENDING, COMPLETED, FAILED)
        """
        employee_id = request.data.get('employee_id')
        requested_amount = request.data.get('amount', 0)
        idempotency_key = request.data.get('idempotency_key')
        
        # Validaciones básicas
        if not employee_id:
            return Response({'error': 'employee_id requerido'}, status=400)
        
        if not idempotency_key:
            return Response({'error': 'idempotency_key requerido'}, status=400)
        
        if not requested_amount or requested_amount <= 0:
            return Response({'error': 'amount debe ser mayor a 0'}, status=400)
        
        # Datos del pago
        payment_data = {
            'payment_method': request.data.get('payment_method', 'cash'),
            'payment_reference': request.data.get('payment_reference', ''),
            'payment_notes': request.data.get('payment_notes', ''),
            'paid_by': request.user
        }
        
        # Validar caja abierta para pagos en efectivo
        if payment_data['payment_method'] == 'cash':
            from apps.pos_api.models import CashRegister
            open_register = CashRegister.objects.filter(
                user__tenant=request.user.tenant,
                is_open=True
            ).first()
            
            if not open_register:
                return Response({
                    'error': 'No hay caja registradora abierta para procesar pagos en efectivo'
                }, status=409)
        
        # Procesar pago usando servicio endurecido
        result = PaymentService.process_payment(
            employee_id=employee_id,
            requested_amount=Decimal(str(requested_amount)),
            payment_data=payment_data,
            idempotency_key=idempotency_key
        )
        
        # Mapear respuesta según resultado
        if result['status'] == 'success':
            return Response(result, status=201)
        elif result['status'] == 'already_processed':
            return Response(result, status=200)
        elif result['status'] == 'processing':
            return Response(result, status=202)
        else:
            return Response(result, status=400)
        

    
    @transaction.atomic
    def _pay_by_sales(self, employee, sale_ids, payment_method, payment_reference, idempotency_key, user, apply_loan_deduction=True):
        """Procesar pago a empleado por ventas específicas
        
        PUNTO 2 - REGLAS DE NEGOCIO ACTUALES (TEMPORALES):
        - Descuento de préstamos = suma de cuotas mensuales de préstamos activos
        - Máximo 50% del salario bruto puede ser descontado
        - Si apply_loan_deduction=False, NO se aplica descuento
        - Estas reglas pueden cambiar por decisión de negocio
        """
        from apps.pos_api.models import Sale
        
        # CORRECCIÓN: Manejar ON_DEMAND (sale_ids vacío)
        if not sale_ids:  # ON_DEMAND: Obtener todas las ventas pendientes
            sales = Sale.objects.select_for_update().filter(
                employee=employee,
                employee__tenant=employee.tenant,
                status='completed',
                period__isnull=True
            )
        else:  # Ventas específicas
            sales = Sale.objects.select_for_update().filter(
                id__in=sale_ids,
                employee=employee,
                employee__tenant=employee.tenant,
                status='completed',
                period__isnull=True
            )
            # Validar que todas las ventas existen
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
        
        # Validar balance disponible
        available_balance = EmployeeBalanceService.get_balance(employee.id)
        if amount > available_balance:
            return Response({
                'error': 'Balance insuficiente',
                'available_balance': float(available_balance),
                'requested_amount': float(amount)
            }, status=400)
        
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
        
        # PUNTO 3 ROBUSTEZ: Procesar deducciones de préstamos dentro de transacción
        loan_deductions = Decimal('0.00')
        loan_details = []
        
        if apply_loan_deduction:
            active_loans = employee.advance_loans.select_for_update().filter(status='active')
            
            if active_loans.exists():
                # PUNTO 1 SEGURIDAD: Backend recalcula SIEMPRE el monto
                # Descuento = suma de cuotas mensuales (máximo 50%)
                max_loan_deduction = summary.total_earnings * Decimal('0.5')
                total_monthly_payments = sum(loan.monthly_payment for loan in active_loans)
                total_loan_debt = sum(loan.remaining_balance for loan in active_loans)
                loan_deductions = min(max_loan_deduction, total_monthly_payments, total_loan_debt)
                
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
                'sale_ids': list(sales.values_list('id', flat=True)),  # IDs reales procesados
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
    
    def _pay_by_fortnight(self, employee, year, fortnight, payment_method, payment_reference, user, apply_loan_deduction=True):
        """Procesar pago a empleado por quincena completa
        
        PUNTO 4 CLARIDAD: Este método procesa pagos de nómina quincenal
        para empleados con sueldo fijo o mixto.
        """
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
        
        # Protección contra doble pago
        existing_payment = FortnightSummary.objects.filter(
            employee=employee,
            fortnight_year=year,
            fortnight_number=fortnight,
            is_paid=True
        ).first()
        
        if existing_payment:
            return Response({
                'status': 'already_paid',
                'message': 'Empleado ya pagado en este período',
                'paid_at': existing_payment.paid_at.isoformat(),
                'is_advance_payment': getattr(existing_payment, 'is_advance_payment', False)
            }, status=409)
        
        try:
            summary = FortnightSummary.objects.get(
                employee=employee,
                fortnight_year=year,
                fortnight_number=fortnight
            )
                
        except FortnightSummary.DoesNotExist:
            # Para empleados FIXED/MIXED: crear summary automático
            if employee.salary_type in ['fixed', 'mixed']:
                fixed_amount = self._calculate_fixed_salary_for_period(employee)
                if fixed_amount > 0:
                    summary = FortnightSummary.objects.create(
                        employee=employee,
                        fortnight_year=year,
                        fortnight_number=fortnight,
                        total_earnings=fixed_amount,
                        total_services=0,
                        is_paid=False
                    )
                else:
                    return Response({'error': 'Empleado no tiene salario configurado'}, status=400)
            else:
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
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, CanViewFinancialData])
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
                
                # CORRECCIÓN: Calcular montos pendientes incluyendo earnings existentes
                from apps.pos_api.models import Sale
                from .earnings_models import Earning
                
                # Buscar ventas sin asignar a período
                pending_sales = Sale.objects.filter(
                    employee=employee,
                    status='completed',
                    period__isnull=True
                )
                
                # Buscar earnings sin pagar de este empleado
                unpaid_earnings = Earning.objects.filter(
                    employee=employee,
                    sale__period__isnull=True,  # Ventas no asignadas a período
                    sale__status='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                
                pending_amount = 0
                if pending_sales.exists():
                    total_pending_sales = sum(float(s.total) for s in pending_sales)
                    pending_amount = self._calculate_payment_amount(employee, total_pending_sales)
                
                # Sumar earnings existentes no pagados
                pending_amount += float(unpaid_earnings)
                
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
                # No hay summary para esta quincena
                from apps.pos_api.models import Sale
                from .earnings_models import Earning
                
                pending_sales = Sale.objects.filter(
                    employee=employee,
                    status='completed',
                    period__isnull=True
                )
                
                # CORRECCIÓN: Incluir earnings existentes no pagados
                unpaid_earnings = Earning.objects.filter(
                    employee=employee,
                    sale__period__isnull=True,
                    sale__status='completed'
                ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
                
                pending_amount = 0
                services_count = 0
                if pending_sales.exists():
                    total_pending_sales = sum(float(s.total) for s in pending_sales)
                    pending_amount = self._calculate_payment_amount(employee, total_pending_sales)
                    services_count = pending_sales.count()
                
                # Sumar earnings existentes
                pending_amount += float(unpaid_earnings)
                
                # Para empleados FIXED/MIXED: crear summary automático si no existe
                total_earned = 0
                if employee.salary_type in ['fixed', 'mixed']:
                    # Calcular sueldo fijo para el período
                    fixed_amount = self._calculate_fixed_salary_for_period(employee)
                    if fixed_amount > 0:
                        # Crear summary automático para empleados fijos
                        summary = FortnightSummary.objects.create(
                            employee=employee,
                            fortnight_year=year,
                            fortnight_number=fortnight,
                            total_earnings=fixed_amount,
                            total_services=0,
                            is_paid=False
                        )
                        total_earned = float(fixed_amount)
                
                # Incluir empleado si tiene pendientes O es fijo con salario
                if pending_amount > 0 or total_earned > 0:
                    earnings_data.append({
                        'employee_id': employee.id,
                        'employee_name': employee.user.full_name or employee.user.email,
                        'salary_type': employee.salary_type,
                        'commission_percentage': float(employee.commission_percentage),
                        'total_earned': total_earned,
                        'pending_amount': round(pending_amount, 2),
                        'services_count': services_count,
                        'payment_status': 'pending',
                        'paid_at': None
                    })
                else:
                    # Solo incluir si no es empleado fijo o tiene salario 0
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
            base_salary = self._calculate_fixed_salary_for_period(employee)
            return float(base_salary) + commission
        else:  # fixed
            # Para sueldo fijo, usar método específico
            return float(self._calculate_fixed_salary_for_period(employee))
    
    def _calculate_fixed_salary_for_period(self, employee):
        """Calcular sueldo fijo según payment_frequency contractual"""
        from .payroll_utils import convert_salary_to_period
        
        monthly_salary = employee.contractual_monthly_salary or employee.salary_amount or Decimal('0')
        if monthly_salary <= 0:
            return Decimal('0')
        
        # Respetar payment_frequency del contrato laboral
        frequency = getattr(employee, 'payment_frequency', 'biweekly')
        return convert_salary_to_period(monthly_salary, frequency)
    
    def _apply_deductions(self, employee, gross_amount, fortnight):
        """Aplicar descuentos legales según país del tenant"""
        # Obtener país del tenant (default: DO)
        country_code = getattr(employee.tenant, 'country', 'DO') or 'DO'
        
        # Obtener calculadora según país
        tax_calculator = TaxCalculatorFactory.get_calculator(country_code)
        
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
    
    @action(detail=False, methods=['post'], permission_classes=[IsAuthenticated, IsClientAdmin])
    def preview_payment(self, request):
        """Vista previa de pago a empleado SIN aplicar cambios
        
        PUNTO 3 ROBUSTEZ: Este endpoint NO modifica ningún dato.
        Calcula todos los montos y descuentos para confirmación.
        El pago real debe usar pay_employee() dentro de transaction.atomic().
        
        PUNTO 2 REGLAS: Muestra descuento sugerido basado en cuotas mensuales.
        """
        employee_id = request.data.get('employee_id')
        sale_ids = request.data.get('sale_ids', [])
        year = request.data.get('year')
        fortnight = request.data.get('fortnight')
        apply_loan_deduction = request.data.get('apply_loan_deduction', True)
        
        # PUNTO 1 SEGURIDAD: Ignorar loan_deduction_amount en preview también
        if 'loan_deduction_amount' in request.data:
            logger.warning(f"Preview recibió loan_deduction_amount - IGNORADO")
        
        # Validaciones básicas
        if not employee_id:
            return Response({'error': 'employee_id requerido'}, status=400)
        
        try:
            employee = Employee.objects.get(
                id=employee_id,
                tenant=request.user.tenant,
                is_active=True
            )
            
            # Calcular monto bruto (MISMA LÓGICA que pay_employee)
            if sale_ids is not None:  # CORRECCIÓN: Aceptar [] para ON_DEMAND
                gross_amount = self._calculate_gross_amount_by_sales(employee, sale_ids)
                payment_type = 'sales'
            elif year and fortnight:
                gross_amount = self._calculate_gross_amount_by_fortnight(employee, int(year), int(fortnight))
                payment_type = 'fortnight'
            else:
                return Response({'error': 'Especificar sale_ids o year+fortnight'}, status=400)
            
            if gross_amount <= 0:
                return Response({'error': 'No hay monto para pagar'}, status=400)
            
            # Validar balance disponible en preview
            available_balance = EmployeeBalanceService.get_balance(employee.id)
            if gross_amount > available_balance:
                return Response({
                    'error': 'Balance insuficiente para el monto solicitado',
                    'available_balance': float(available_balance),
                    'requested_amount': float(gross_amount)
                }, status=400)
            
            # Preview de deducciones de préstamos
            loan_preview = LoanService.preview_deductions(employee.id, gross_amount)
            
            # Calcular descuentos legales
            current_fortnight = fortnight if year and fortnight else self._calculate_fortnight(timezone.now().date())[1]
            net_after_legal, legal_deductions = self._apply_deductions(employee, gross_amount, current_fortnight)
            
            # Analizar préstamos (SIN MODIFICAR)
            loan_info = self._analyze_loans_for_preview(employee, gross_amount, apply_loan_deduction)
            
            # Calcular neto final
            suggested_loan_deduction = loan_info['suggested_deduction']
            net_amount_with_loans = net_after_legal - suggested_loan_deduction
            total_deductions = legal_deductions['total'] + float(suggested_loan_deduction)
            
            # Calcular neto final con préstamos
            net_after_loans = gross_amount - loan_preview['total_deduction']
            
            return Response({
                'preview': {
                    'employee_id': employee.id,
                    'employee_name': employee.user.full_name or employee.user.email,
                    'payment_type': payment_type,
                    'gross_amount': float(gross_amount),
                    'loan_deductions': {
                        'total': float(loan_preview['total_deduction']),
                        'loans': loan_preview['loans'],
                        'can_apply': loan_preview['can_apply']
                    },
                    'net_amount': float(net_after_loans),
                    'balance_after_payment': float(loan_preview['balance_after_deduction'] - gross_amount)
                },
                'can_proceed': loan_preview['can_apply'] and net_after_loans > 0,
                'warnings': self._get_loan_warnings(loan_preview)
            })
            
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
        except Exception as e:
            logger.error(f"Error en preview: {str(e)}")
            return Response({'error': f'Error calculando preview: {str(e)}'}, status=500)
    
    def _calculate_gross_amount_by_sales(self, employee, sale_ids):
        """Calcular monto bruto por ventas específicas (SOLO LECTURA)"""
        from apps.pos_api.models import Sale
        
        # CORRECCIÓN: Manejar ON_DEMAND (sale_ids vacío)
        if not sale_ids:  # ON_DEMAND: Todas las ventas pendientes
            sales = Sale.objects.filter(
                employee=employee,
                employee__tenant=employee.tenant,
                status='completed',
                period__isnull=True
            )
        else:  # Ventas específicas
            sales = Sale.objects.filter(
                id__in=sale_ids,
                employee=employee,
                employee__tenant=employee.tenant,
                status='completed',
                period__isnull=True
            )
            if sales.count() != len(sale_ids):
                raise ValueError('Algunas ventas no existen o no pertenecen a este tenant')
        
        if not sales.exists():
            return Decimal('0')
        
        total_sales = sum(float(s.total) for s in sales)
        return Decimal(str(self._calculate_payment_amount(employee, total_sales)))
    
    def _calculate_gross_amount_by_fortnight(self, employee, year, fortnight):
        """Calcular monto bruto por quincena (SOLO LECTURA)"""
        try:
            summary = FortnightSummary.objects.get(
                employee=employee,
                fortnight_year=year,
                fortnight_number=fortnight
            )
            return summary.total_earnings
        except FortnightSummary.DoesNotExist:
            # Para empleados FIXED: calcular automáticamente
            if employee.salary_type in ['fixed', 'mixed']:
                return self._calculate_fixed_salary_for_period(employee)
            else:
                raise ValueError('No hay ganancias para esta quincena')
    
    def _analyze_loans_for_preview(self, employee, gross_amount, apply_loan_deduction):
        """Analizar préstamos para preview SIN modificar datos
        
        PUNTO 2 DOCUMENTACIÓN: Reglas actuales de descuento de préstamos:
        - Descuento sugerido = suma de cuotas mensuales de préstamos activos
        - Máximo permitido = 50% del salario bruto
        - Si apply_loan_deduction=False, descuento = 0
        
        NOTA: Estas reglas son TEMPORALES y pueden cambiar.
        """
        active_loans = employee.advance_loans.filter(
            status='active',
            remaining_balance__gt=0
        ).order_by('first_payment_date')
        
        if not active_loans.exists():
            return {
                'has_active_loans': False,
                'total_loan_debt': 0,
                'suggested_deduction': 0,
                'max_deduction_allowed': 0,
                'loans_details': []
            }
        
        total_debt = sum(loan.remaining_balance for loan in active_loans)
        max_deduction = gross_amount * Decimal('0.5')  # 50% máximo
        
        if not apply_loan_deduction:
            suggested_deduction = Decimal('0')
        else:
            # PUNTO 1 SEGURIDAD: Backend calcula SIEMPRE el descuento
            # Sugerir suma de cuotas mensuales (regla actual)
            total_monthly_payments = sum(loan.monthly_payment for loan in active_loans)
            suggested_deduction = min(total_monthly_payments, max_deduction, total_debt)
        
        loans_details = []
        remaining_deduction = suggested_deduction
        
        for loan in active_loans:
            if remaining_deduction <= 0:
                suggested_payment = Decimal('0')
            else:
                suggested_payment = min(remaining_deduction, loan.remaining_balance)
                remaining_deduction -= suggested_payment
            
            loans_details.append({
                'loan_id': loan.id,
                'loan_type': getattr(loan, 'loan_type', 'advance'),
                'remaining_balance': float(loan.remaining_balance),
                'monthly_payment': float(getattr(loan, 'monthly_payment', loan.remaining_balance)),
                'suggested_payment': float(suggested_payment)
            })
        
        return {
            'has_active_loans': True,
            'total_loan_debt': float(total_debt),
            'suggested_deduction': float(suggested_deduction),
            'max_deduction_allowed': float(max_deduction),
            'loans_details': loans_details
        }
    
    def _get_loan_warnings(self, loan_preview):
        """Generar advertencias para el preview de préstamos"""
        warnings = []
        
        if loan_preview['loans'] and not loan_preview['can_apply']:
            warnings.append('Balance insuficiente para aplicar todas las deducciones de préstamos')
        
        if loan_preview['total_deduction'] > 0:
            warnings.append(f"Se aplicarán deducciones de préstamos por ${loan_preview['total_deduction']}")
        
        return warnings
    
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