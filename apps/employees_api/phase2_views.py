from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Employee
from .advance_loans import AdvanceLoan, LoanPayment
from .payroll_reports import PayrollReportGenerator
from .accounting_integration import AccountingIntegrator, AccountingEntry
from .notifications import PayrollNotificationService
import logging

logger = logging.getLogger(__name__)

class AdvanceLoanViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Listar préstamos del tenant"""
        loans = AdvanceLoan.objects.filter(
            employee__tenant=request.user.tenant
        ).select_related('employee', 'employee__user').order_by('-created_at')
        
        data = []
        for loan in loans:
            data.append({
                'id': loan.id,
                'employee_name': getattr(loan.employee.user, 'full_name', None) or loan.employee.user.email,
                'loan_type': loan.get_loan_type_display(),
                'amount': float(loan.amount),
                'status': loan.get_status_display(),
                'installments': loan.installments,
                'monthly_payment': float(loan.monthly_payment),
                'remaining_balance': float(loan.remaining_balance),
                'request_date': loan.request_date,
                'approval_date': loan.approval_date
            })
        
        return Response({'loans': data})
    
    def create(self, request):
        """Crear nueva solicitud de préstamo"""
        employee_id = request.data.get('employee_id')
        loan_type = request.data.get('loan_type')
        amount = request.data.get('amount')
        reason = request.data.get('reason', '').strip()
        installments = request.data.get('installments', 1)
        
        # Validaciones de seguridad
        if not amount or amount <= 0:
            return Response({'error': 'Monto debe ser mayor a 0'}, status=400)
        if amount > 100000:  # Límite máximo
            return Response({'error': 'Monto excede límite máximo (RD$100,000)'}, status=400)
        if installments < 1 or installments > 24:
            return Response({'error': 'Cuotas deben estar entre 1 y 24'}, status=400)
        if len(reason) > 500:
            return Response({'error': 'Motivo demasiado largo (máx. 500 caracteres)'}, status=400)
        
        try:
            employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant, is_active=True)
            
            with transaction.atomic():
                loan = AdvanceLoan.objects.create(
                    employee=employee,
                    loan_type=loan_type,
                    amount=amount,
                    reason=reason,
                    installments=installments
                )
                
                # Log de auditoría
                logger.info(f'Préstamo creado - ID: {loan.id}, Empleado: {employee.user.email}, Monto: {amount}, Usuario: {request.user.id}')
                
                # Sin límites - cualquier empleado puede solicitar préstamos
                
                return Response({
                    'message': 'Solicitud creada',
                    'loan_id': loan.id,
                    'status': loan.status
                })
                
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
    
    @action(detail=True, methods=['post'])
    def request_cancellation(self, request, pk=None):
        """Solicitar cancelación de préstamo"""
        reason = request.data.get('reason', '').strip()
        
        if not reason:
            return Response({'error': 'Motivo de cancelación requerido'}, status=400)
        if len(reason) > 500:
            return Response({'error': 'Motivo demasiado largo (máx. 500 caracteres)'}, status=400)
        
        try:
            loan = AdvanceLoan.objects.get(
                id=pk, 
                employee__tenant=request.user.tenant,
                status='active'
            )
            
            loan.status = 'pending_cancellation'
            loan.cancellation_requested_by = request.user
            loan.cancellation_reason = reason
            loan.cancellation_requested_at = timezone.now()
            loan.save()
            
            return Response({'message': 'Solicitud de cancelación enviada para aprobación'})
                
        except AdvanceLoan.DoesNotExist:
            return Response({'error': 'Préstamo no encontrado'}, status=404)
    
    @action(detail=True, methods=['post'])
    def approve_cancellation(self, request, pk=None):
        """Aprobar cancelación de préstamo"""
        try:
            loan = AdvanceLoan.objects.get(
                id=pk, 
                employee__tenant=request.user.tenant,
                status='pending_cancellation'
            )
            
            # Calcular saldo real
            total_paid = sum(payment.amount for payment in loan.payments.all())
            real_balance = loan.amount - total_paid
            
            if real_balance > 0:
                return Response({
                    'error': f'El empleado debe ${real_balance:.2f}. Debe pagarse antes de cancelar.',
                    'pending_balance': float(real_balance)
                }, status=400)
            
            loan.status = 'cancelled'
            loan.cancelled_by = request.user
            loan.cancelled_at = timezone.now()
            loan.save()
            
            # Log de auditoría
            logger.info(f'Préstamo {loan.id} cancelado por usuario {request.user.id} - Empleado: {loan.employee.user.email}')
            
            return Response({'message': 'Préstamo cancelado exitosamente'})
                
        except AdvanceLoan.DoesNotExist:
            return Response({'error': 'Solicitud de cancelación no encontrada'}, status=404)
    
    @action(detail=True, methods=['post'])
    def reject_cancellation(self, request, pk=None):
        """Rechazar cancelación de préstamo"""
        try:
            loan = AdvanceLoan.objects.get(
                id=pk, 
                employee__tenant=request.user.tenant,
                status='pending_cancellation'
            )
            
            loan.status = 'active'
            loan.cancellation_requested_by = None
            loan.cancellation_reason = ''
            loan.cancellation_requested_at = None
            loan.save()
            
            return Response({'message': 'Solicitud de cancelación rechazada'})
                
        except AdvanceLoan.DoesNotExist:
            return Response({'error': 'Solicitud de cancelación no encontrada'}, status=404)

class PayrollReportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        """LEGACY: Usar payroll_api.PayrollSettlement"""
        return Response({
            'error': 'Endpoint legacy deshabilitado - usar /api/payroll/settlements/'
        }, status=410)
    
    @action(detail=False, methods=['get'])
    def employee_annual(self, request):
        """LEGACY: Usar payroll_api.PayrollSettlement"""
        return Response({
            'error': 'Endpoint legacy deshabilitado - usar /api/payroll/settlements/'
        }, status=410)
    
    @action(detail=False, methods=['get'])
    def tax_compliance(self, request):
        """LEGACY: Usar payroll_api.PayrollSettlement"""
        return Response({
            'error': 'Endpoint legacy deshabilitado - usar /api/payroll/settlements/'
        }, status=410)
    
    @action(detail=False, methods=['get'])
    def loans_summary(self, request):
        """LEGACY: Usar AdvanceLoanViewSet.list()"""
        return Response({
            'error': 'Endpoint legacy deshabilitado - usar /api/employees/loans/'
        }, status=410)

class AccountingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """LEGACY: Usar payroll_api.PayrollSettlement"""
        return Response({
            'error': 'Endpoint legacy deshabilitado - usar /api/payroll/settlements/'
        }, status=410)
    
    @action(detail=False, methods=['post'])
    def export_quickbooks(self, request):
        """LEGACY: Usar payroll_api.PayrollSettlement"""
        return Response({
            'error': 'Endpoint legacy deshabilitado - usar /api/payroll/settlements/'
        }, status=410)
    
    @action(detail=False, methods=['get'])
    def trial_balance(self, request):
        """LEGACY: Usar payroll_api.PayrollSettlement"""
        return Response({
            'error': 'Endpoint legacy deshabilitado - usar /api/payroll/settlements/'
        }, status=410)
    
    @action(detail=False, methods=['post'])
    def generate_employer_contributions(self, request):
        """LEGACY: Usar payroll_api.PayrollSettlement"""
        return Response({
            'error': 'Endpoint legacy deshabilitado - usar /api/payroll/settlements/'
        }, status=410)