from django.db import models
from django.utils import timezone
from decimal import Decimal
from datetime import datetime
import json
from .models import Employee
from .earnings_models import FortnightSummary

class AccountingEntry(models.Model):
    ENTRY_TYPES = [
        ('payroll', 'Nómina'),
        ('tax_provision', 'Provisión Impuestos'),
        ('loan_disbursement', 'Desembolso Préstamo'),
        ('loan_payment', 'Pago Préstamo')
    ]
    
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES)
    reference_id = models.CharField(max_length=50)  # ID del pago o préstamo
    entry_date = models.DateField()
    description = models.TextField()
    
    # Cuentas contables
    debit_account = models.CharField(max_length=20)
    credit_account = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Metadatos
    tenant = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    exported = models.BooleanField(default=False)
    export_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-entry_date', '-created_at']

class ChartOfAccounts:
    """Plan de cuentas estándar para peluquerías"""
    
    ACCOUNTS = {
        # Activos
        '1110': 'Efectivo en Caja',
        '1120': 'Bancos',
        '1210': 'Cuentas por Cobrar Empleados',
        
        # Pasivos
        '2110': 'Cuentas por Pagar Empleados',
        '2120': 'AFP por Pagar',
        '2130': 'SFS por Pagar',
        '2140': 'ISR por Pagar',
        '2150': 'Préstamos Empleados por Pagar',
        
        # Gastos
        '5110': 'Sueldos y Salarios',
        '5120': 'Comisiones',
        '5130': 'Contribuciones Patronales AFP',
        '5140': 'Contribuciones Patronales SFS',
        '5150': 'Contribuciones SRL',
        '5160': 'Gastos Financieros Préstamos'
    }

class AccountingIntegrator:
    
    @staticmethod
    def create_payroll_entries(fortnight_summary):
        """Crea asientos contables para un pago de nómina"""
        entries = []
        
        # Asiento principal de nómina
        entries.extend([
            # Débito: Gasto de sueldos
            AccountingEntry(
                entry_type='payroll',
                reference_id=f'PAY-{fortnight_summary.id}',
                entry_date=fortnight_summary.paid_at.date(),
                description=f'Nómina {getattr(fortnight_summary.employee.user, "full_name", None) or fortnight_summary.employee.user.email} - {fortnight_summary.paid_at.date()}',
                debit_account='5110' if fortnight_summary.employee.salary_type == 'fixed' else '5120',
                credit_account='2110',
                amount=fortnight_summary.total_earnings,
                tenant=fortnight_summary.employee.tenant.name
            ),
            
            # Crédito: Cuentas por pagar empleados (neto)
            AccountingEntry(
                entry_type='payroll',
                reference_id=f'PAY-{fortnight_summary.id}',
                entry_date=fortnight_summary.paid_at.date(),
                description=f'Pago neto {getattr(fortnight_summary.employee.user, "full_name", None) or fortnight_summary.employee.user.email}',
                debit_account='2110',
                credit_account='1120',
                amount=fortnight_summary.net_salary,
                tenant=fortnight_summary.employee.tenant.name
            )
        ])
        
        # Asientos de deducciones
        if fortnight_summary.afp_deduction > 0:
            entries.append(AccountingEntry(
                entry_type='payroll',
                reference_id=f'PAY-{fortnight_summary.id}',
                entry_date=fortnight_summary.paid_at.date(),
                description=f'AFP empleado {getattr(fortnight_summary.employee.user, "full_name", None) or fortnight_summary.employee.user.email}',
                debit_account='2110',
                credit_account='2120',
                amount=fortnight_summary.afp_deduction,
                tenant=fortnight_summary.employee.tenant.name
            ))
        
        if fortnight_summary.sfs_deduction > 0:
            entries.append(AccountingEntry(
                entry_type='payroll',
                reference_id=f'PAY-{fortnight_summary.id}',
                entry_date=fortnight_summary.paid_at.date(),
                description=f'SFS empleado {getattr(fortnight_summary.employee.user, "full_name", None) or fortnight_summary.employee.user.email}',
                debit_account='2110',
                credit_account='2130',
                amount=fortnight_summary.sfs_deduction,
                tenant=fortnight_summary.employee.tenant.name
            ))
        
        if fortnight_summary.isr_deduction > 0:
            entries.append(AccountingEntry(
                entry_type='payroll',
                reference_id=f'PAY-{fortnight_summary.id}',
                entry_date=fortnight_summary.paid_at.date(),
                description=f'ISR empleado {getattr(fortnight_summary.employee.user, "full_name", None) or fortnight_summary.employee.user.email}',
                debit_account='2110',
                credit_account='2140',
                amount=fortnight_summary.isr_deduction,
                tenant=fortnight_summary.employee.tenant.name
            ))
        
        # Guardar asientos
        for entry in entries:
            entry.save()
        
        return entries
    
    @staticmethod
    def create_employer_contribution_entries(tenant, month, year):
        """Crea asientos de contribuciones patronales mensuales"""
        from datetime import datetime
        import calendar
        
        start_date = datetime(year, month, 1).date()
        end_date = datetime(year, month, calendar.monthrange(year, month)[1]).date()
        
        # Obtener todos los pagos del mes
        payments = FortnightSummary.objects.filter(
            employee__tenant__name=tenant,
            paid_at__date__range=[start_date, end_date],
            is_paid=True
        )
        
        total_afp_employee = sum(p.afp_deduction for p in payments)
        total_sfs_employee = sum(p.sfs_deduction for p in payments)
        total_gross = sum(p.total_earnings for p in payments)
        
        # Calcular contribuciones patronales
        afp_employer = total_afp_employee * Decimal('2.47')  # 7.10% / 2.87% = 2.47
        sfs_employer = total_sfs_employee * Decimal('2.33')  # 7.09% / 3.04% = 2.33
        srl_employer = total_gross * Decimal('0.012')  # 1.2%
        
        entries = []
        
        if afp_employer > 0:
            entries.append(AccountingEntry(
                entry_type='tax_provision',
                reference_id=f'AFP-EMP-{year}-{month:02d}',
                entry_date=end_date,
                description=f'Contribución patronal AFP {calendar.month_name[month]} {year}',
                debit_account='5130',
                credit_account='2120',
                amount=afp_employer,
                tenant=tenant
            ))
        
        if sfs_employer > 0:
            entries.append(AccountingEntry(
                entry_type='tax_provision',
                reference_id=f'SFS-EMP-{year}-{month:02d}',
                entry_date=end_date,
                description=f'Contribución patronal SFS {calendar.month_name[month]} {year}',
                debit_account='5140',
                credit_account='2130',
                amount=sfs_employer,
                tenant=tenant
            ))
        
        if srl_employer > 0:
            entries.append(AccountingEntry(
                entry_type='tax_provision',
                reference_id=f'SRL-{year}-{month:02d}',
                entry_date=end_date,
                description=f'Seguro de Riesgos Laborales {calendar.month_name[month]} {year}',
                debit_account='5150',
                credit_account='2130',
                amount=srl_employer,
                tenant=tenant
            ))
        
        # Guardar asientos
        for entry in entries:
            entry.save()
        
        return entries
    
    @staticmethod
    def export_to_quickbooks(tenant, start_date, end_date):
        """Exporta asientos contables en formato QuickBooks IIF"""
        entries = AccountingEntry.objects.filter(
            tenant=tenant,
            entry_date__range=[start_date, end_date],
            exported=False
        ).order_by('entry_date', 'reference_id')
        
        iif_content = ['!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tCLASS\tAMOUNT\tDOCNUM\tMEMO']
        iif_content.append('!SPL\tSPLID\tTRNSTYPE\tDATE\tACCNT\tNAME\tCLASS\tAMOUNT\tDOCNUM\tMEMO')
        iif_content.append('!ENDTRNS')
        
        current_ref = None
        for entry in entries:
            if entry.reference_id != current_ref:
                # Nueva transacción
                iif_content.append(f'TRNS\tJOURNAL\t{entry.entry_date.strftime("%m/%d/%Y")}\t{entry.debit_account}\t\t\t{entry.amount}\t{entry.reference_id}\t{entry.description}')
                current_ref = entry.reference_id
            
            # Líneas de detalle
            iif_content.append(f'SPL\t\tJOURNAL\t{entry.entry_date.strftime("%m/%d/%Y")}\t{entry.credit_account}\t\t\t-{entry.amount}\t{entry.reference_id}\t{entry.description}')
            iif_content.append('ENDTRNS')
        
        # Marcar como exportados
        entries.update(exported=True, export_date=timezone.now())
        
        return '\n'.join(iif_content)
    
    @staticmethod
    def generate_trial_balance(tenant, date):
        """Genera balance de comprobación"""
        entries = AccountingEntry.objects.filter(
            tenant=tenant,
            entry_date__lte=date
        )
        
        balances = {}
        
        for entry in entries:
            # Débitos
            if entry.debit_account not in balances:
                balances[entry.debit_account] = {'debit': Decimal('0'), 'credit': Decimal('0')}
            balances[entry.debit_account]['debit'] += entry.amount
            
            # Créditos
            if entry.credit_account not in balances:
                balances[entry.credit_account] = {'debit': Decimal('0'), 'credit': Decimal('0')}
            balances[entry.credit_account]['credit'] += entry.amount
        
        # Formatear resultado
        trial_balance = []
        for account, balance in balances.items():
            net_balance = balance['debit'] - balance['credit']
            trial_balance.append({
                'account': account,
                'account_name': ChartOfAccounts.ACCOUNTS.get(account, 'Cuenta Desconocida'),
                'debit': balance['debit'],
                'credit': balance['credit'],
                'net_balance': net_balance
            })
        
        return sorted(trial_balance, key=lambda x: x['account'])