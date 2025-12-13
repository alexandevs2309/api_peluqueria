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
                'employee_name': loan.employee.user.full_name,
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
        reason = request.data.get('reason', '')
        installments = request.data.get('installments', 1)
        
        try:
            employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
            
            with transaction.atomic():
                loan = AdvanceLoan.objects.create(
                    employee=employee,
                    loan_type=loan_type,
                    amount=amount,
                    reason=reason,
                    installments=installments
                )
                
                # Sin límites - cualquier empleado puede solicitar préstamos
                
                return Response({
                    'message': 'Solicitud creada',
                    'loan_id': loan.id,
                    'status': loan.status
                })
                
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Cancelar préstamo"""
        try:
            loan = AdvanceLoan.objects.get(
                id=pk, 
                employee__tenant=request.user.tenant,
                status='active'
            )
            
            loan.status = 'cancelled'
            loan.save()
            
            return Response({'message': 'Préstamo cancelado'})
                
        except AdvanceLoan.DoesNotExist:
            return Response({'error': 'Préstamo no encontrado'}, status=404)

class PayrollReportViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def monthly_summary(self, request):
        """Resumen mensual de nómina"""
        year = int(request.GET.get('year', timezone.now().year))
        month = int(request.GET.get('month', timezone.now().month))
        
        report = PayrollReportGenerator.monthly_payroll_summary(
            year, month, request.user.tenant
        )
        
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def employee_annual(self, request):
        """Reporte anual de empleado"""
        employee_id = request.GET.get('employee_id')
        year = int(request.GET.get('year', timezone.now().year))
        
        if not employee_id:
            return Response({'error': 'employee_id requerido'}, status=400)
        
        try:
            employee = Employee.objects.get(id=employee_id, tenant=request.user.tenant)
            report = PayrollReportGenerator.employee_annual_report(employee_id, year)
            return Response(report)
        except Employee.DoesNotExist:
            return Response({'error': 'Empleado no encontrado'}, status=404)
    
    @action(detail=False, methods=['get'])
    def tax_compliance(self, request):
        """Reporte de cumplimiento fiscal"""
        year = int(request.GET.get('year', timezone.now().year))
        month = int(request.GET.get('month', timezone.now().month))
        
        report = PayrollReportGenerator.tax_compliance_report(
            year, month, request.user.tenant
        )
        
        return Response(report)
    
    @action(detail=False, methods=['get'])
    def loans_summary(self, request):
        """Resumen de préstamos"""
        status_filter = request.GET.get('status')
        
        report = PayrollReportGenerator.loans_report(
            request.user.tenant, status_filter
        )
        
        return Response(report)

class AccountingViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    
    def list(self, request):
        """Listar asientos contables"""
        entries = AccountingEntry.objects.filter(
            tenant=request.user.tenant.name
        ).order_by('-entry_date')[:100]
        
        data = []
        for entry in entries:
            data.append({
                'id': entry.id,
                'entry_type': entry.get_entry_type_display(),
                'reference_id': entry.reference_id,
                'entry_date': entry.entry_date,
                'description': entry.description,
                'debit_account': entry.debit_account,
                'credit_account': entry.credit_account,
                'amount': float(entry.amount),
                'exported': entry.exported
            })
        
        return Response({'entries': data})
    
    @action(detail=False, methods=['post'])
    def export_quickbooks(self, request):
        """Exportar a QuickBooks"""
        start_date = request.data.get('start_date')
        end_date = request.data.get('end_date')
        
        if not start_date or not end_date:
            return Response({'error': 'Fechas requeridas'}, status=400)
        
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            
            iif_content = AccountingIntegrator.export_to_quickbooks(
                request.user.tenant.name, start_date, end_date
            )
            
            return Response({
                'message': 'Exportación completada',
                'iif_content': iif_content
            })
            
        except ValueError:
            return Response({'error': 'Formato de fecha inválido'}, status=400)
    
    @action(detail=False, methods=['get'])
    def trial_balance(self, request):
        """Balance de comprobación"""
        date_str = request.GET.get('date', timezone.now().date().isoformat())
        
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
            balance = AccountingIntegrator.generate_trial_balance(
                request.user.tenant.name, date
            )
            
            return Response({'trial_balance': balance})
            
        except ValueError:
            return Response({'error': 'Formato de fecha inválido'}, status=400)
    
    @action(detail=False, methods=['post'])
    def generate_employer_contributions(self, request):
        """Generar contribuciones patronales"""
        year = int(request.data.get('year', timezone.now().year))
        month = int(request.data.get('month', timezone.now().month))
        
        try:
            entries = AccountingIntegrator.create_employer_contribution_entries(
                request.user.tenant.name, month, year
            )
            
            return Response({
                'message': f'Generadas {len(entries)} contribuciones patronales',
                'entries_count': len(entries)
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=500)