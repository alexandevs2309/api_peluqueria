"""
Management command para migrar datos de payroll a nueva arquitectura
python manage.py migrate_payroll_data
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.payroll_api.models import PayrollSettlement
from apps.payroll_api.models_new import PayrollPeriod, PayrollCalculation
import structlog

logger = structlog.get_logger(__name__)

class Command(BaseCommand):
    help = 'Migrate existing payroll data to new architecture'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without making changes',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # 1. Migrar PayrollSettlements a PayrollPeriods
        self._migrate_periods(dry_run)
        
        # 2. Migrar cálculos existentes
        self._migrate_calculations(dry_run)
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('Payroll data migration completed successfully')
            )
    
    def _migrate_periods(self, dry_run):
        """Migrar settlements únicos a periods"""
        unique_periods = PayrollSettlement.objects.values(
            'tenant', 'frequency', 'period_year', 'period_index',
            'period_start', 'period_end'
        ).distinct()
        
        periods_to_create = []
        
        for period_data in unique_periods:
            if not dry_run:
                period, created = PayrollPeriod.objects.get_or_create(
                    tenant_id=period_data['tenant'],
                    frequency=period_data['frequency'],
                    period_year=period_data['period_year'],
                    period_index=period_data['period_index'],
                    defaults={
                        'period_start': period_data['period_start'],
                        'period_end': period_data['period_end'],
                        'status': 'CLOSED'
                    }
                )
                if created:
                    periods_to_create.append(period)
            else:
                periods_to_create.append(period_data)
        
        self.stdout.write(
            f'{"Would create" if dry_run else "Created"} {len(periods_to_create)} periods'
        )
    
    def _migrate_calculations(self, dry_run):
        """Migrar settlements a calculations"""
        settlements = PayrollSettlement.objects.select_related(
            'employee', 'tenant'
        ).all()
        
        calculations_created = 0
        
        for settlement in settlements:
            try:
                if not dry_run:
                    # Encontrar período correspondiente
                    period = PayrollPeriod.objects.get(
                        tenant=settlement.tenant,
                        frequency=settlement.frequency,
                        period_year=settlement.period_year,
                        period_index=settlement.period_index
                    )
                    
                    # Crear breakdown básico desde datos existentes
                    breakdown = {
                        'migrated_from_settlement': str(settlement.settlement_id),
                        'migration_timestamp': timezone.now().isoformat(),
                        'base_salary': str(settlement.fixed_salary_amount),
                        'commissions': {
                            'total': str(settlement.commission_amount),
                            'details': []
                        },
                        'gross_total': str(settlement.gross_amount),
                        'deductions': {
                            'legal': str(settlement.afp_deduction + settlement.sfs_deduction + settlement.isr_deduction),
                            'loans': str(settlement.total_deductions - settlement.afp_deduction - settlement.sfs_deduction - settlement.isr_deduction),
                            'total': str(settlement.total_deductions)
                        },
                        'net_amount': str(settlement.net_amount)
                    }
                    
                    PayrollCalculation.objects.create(
                        employee=settlement.employee,
                        period=period,
                        tenant=settlement.tenant,
                        version=1,
                        is_current=True,
                        calculation_breakdown=breakdown,
                        base_salary=settlement.fixed_salary_amount,
                        commission_total=settlement.commission_amount,
                        bonuses_total=0,
                        gross_total=settlement.gross_amount,
                        legal_deductions=settlement.afp_deduction + settlement.sfs_deduction + settlement.isr_deduction,
                        loan_deductions=settlement.total_deductions - settlement.afp_deduction - settlement.sfs_deduction - settlement.isr_deduction,
                        other_deductions=0,
                        total_deductions=settlement.total_deductions,
                        net_amount=settlement.net_amount,
                        calculated_by=settlement.closed_by
                    )
                
                calculations_created += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error migrating settlement {settlement.id}: {e}')
                )
                continue
        
        self.stdout.write(
            f'{"Would migrate" if dry_run else "Migrated"} {calculations_created} calculations'
        )