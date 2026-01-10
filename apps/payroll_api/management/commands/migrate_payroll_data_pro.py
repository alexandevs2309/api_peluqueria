"""Management command profesional para migración de payroll"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.payroll_api.models import PayrollSettlement, PayrollPeriod, PayrollCalculation
import structlog

logger = structlog.get_logger("apps.payroll_api")

class Command(BaseCommand):
    help = 'Migrate existing payroll data to new architecture'
    
    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Show what would be migrated')
        parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing')
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        batch_size = options['batch_size']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        logger.info("payroll_migration_started", dry_run=dry_run, batch_size=batch_size)
        
        try:
            periods_created = self._migrate_periods(dry_run, batch_size)
            calculations_created = self._migrate_calculations(dry_run, batch_size)
            
            if not dry_run:
                self._validate_migration()
            
            logger.info("payroll_migration_completed", 
                       periods_created=periods_created,
                       calculations_created=calculations_created)
            
            self.stdout.write(
                self.style.SUCCESS(f'Migration completed: {periods_created} periods, {calculations_created} calculations')
            )
            
        except Exception as e:
            logger.error("payroll_migration_failed", error=str(e), exc_info=True)
            raise
    
    def _migrate_periods(self, dry_run, batch_size):
        """Migrar settlements únicos a periods"""
        unique_periods = PayrollSettlement.objects.values(
            'tenant', 'frequency', 'period_year', 'period_index',
            'period_start', 'period_end'
        ).distinct()
        
        periods_created = 0
        
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
                    periods_created += 1
                    logger.info("period_migrated", 
                               period_id=str(period.period_id),
                               tenant_id=period.tenant_id,
                               frequency=period.frequency)
            else:
                periods_created += 1
        
        return periods_created
    
    def _migrate_calculations(self, dry_run, batch_size):
        """Migrar settlements a calculations con breakdown"""
        settlements = PayrollSettlement.objects.select_related(
            'employee', 'tenant'
        ).order_by('id')
        
        calculations_created = 0
        
        for settlement in settlements.iterator(chunk_size=batch_size):
            try:
                if not dry_run:
                    with transaction.atomic():
                        period = PayrollPeriod.objects.get(
                            tenant=settlement.tenant,
                            frequency=settlement.frequency,
                            period_year=settlement.period_year,
                            period_index=settlement.period_index
                        )
                        
                        breakdown = self._create_legacy_breakdown(settlement)
                        
                        calculation, created = PayrollCalculation.objects.get_or_create(
                            employee=settlement.employee,
                            period=period,
                            version=1,
                            defaults={
                                'tenant': settlement.tenant,
                                'is_current': True,
                                'calculation_breakdown': breakdown,
                                'base_salary': settlement.fixed_salary_amount,
                                'commission_total': settlement.commission_amount,
                                'bonuses_total': 0,
                                'gross_total': settlement.gross_amount,
                                'legal_deductions': settlement.afp_deduction + settlement.sfs_deduction + settlement.isr_deduction,
                                'loan_deductions': settlement.loan_deductions,
                                'other_deductions': 0,
                                'total_deductions': settlement.total_deductions,
                                'net_amount': settlement.net_amount,
                                'calculated_by': settlement.closed_by
                            }
                        )
                        
                        if created:
                            calculations_created += 1
                            logger.info("calculation_migrated",
                                       calculation_id=str(calculation.calculation_id),
                                       employee_id=settlement.employee.id,
                                       legacy_settlement_id=str(settlement.settlement_id))
                
                else:
                    calculations_created += 1
                    
            except Exception as e:
                logger.error("settlement_migration_failed",
                           settlement_id=str(settlement.settlement_id),
                           error=str(e))
                if not dry_run:
                    raise
        
        return calculations_created
    
    def _create_legacy_breakdown(self, settlement):
        """Crear breakdown desde settlement legacy"""
        return {
            'migration_metadata': {
                'source': 'legacy_migration',
                'legacy_settlement_id': str(settlement.settlement_id),
                'migrated_at': timezone.now().isoformat(),
                'version': 'v1_legacy'
            },
            'base_salary': {
                'amount': str(settlement.fixed_salary_amount),
                'calculation_method': 'legacy_fixed_amount'
            },
            'commissions': {
                'total': str(settlement.commission_amount),
                'details': [],
                'note': 'Migrated from legacy system - no detailed breakdown available'
            },
            'bonuses': {
                'total': '0.00',
                'details': []
            },
            'gross_total': str(settlement.gross_amount),
            'deductions': {
                'legal': {
                    'afp': str(settlement.afp_deduction),
                    'sfs': str(settlement.sfs_deduction),
                    'isr': str(settlement.isr_deduction),
                    'total': str(settlement.afp_deduction + settlement.sfs_deduction + settlement.isr_deduction)
                },
                'loans': str(settlement.loan_deductions),
                'other': '0.00',
                'total': str(settlement.total_deductions)
            },
            'net_amount': str(settlement.net_amount)
        }
    
    def _validate_migration(self):
        """Validar consistencia post-migración"""
        settlements_count = PayrollSettlement.objects.count()
        calculations_count = PayrollCalculation.objects.filter(
            calculation_breakdown__migration_metadata__source='legacy_migration'
        ).count()
        
        if settlements_count != calculations_count:
            raise ValueError(f"Migration inconsistency: {settlements_count} settlements vs {calculations_count} calculations")
        
        logger.info("migration_validation_passed",
                   settlements_count=settlements_count,
                   calculations_count=calculations_count)