import json
import logging
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.employees_api.earnings_models import Earning, FortnightSummary, PeriodSummary
from apps.employees_api.models import Employee

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Migrar PeriodSummary a FortnightSummary y corregir datos de earnings'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Solo mostrar cambios sin aplicar')
        parser.add_argument('--commit', action='store_true', help='Aplicar cambios a la base de datos')

    def handle(self, *args, **options):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f'/tmp/earnings_migration_{timestamp}.json'
        
        migration_log = {
            'timestamp': timestamp,
            'dry_run': options['dry_run'],
            'stats': {},
            'errors': [],
            'changes': []
        }

        try:
            with transaction.atomic():
                # 1. Corregir Earnings sin year/fortnight
                self.stdout.write('🔍 Corrigiendo Earnings sin year/fortnight...')
                earnings_fixed = self.fix_earnings_without_fortnight(migration_log)
                
                # 2. Migrar PeriodSummary a FortnightSummary
                self.stdout.write('📦 Migrando PeriodSummary a FortnightSummary...')
                periods_migrated = self.migrate_period_summaries(migration_log)
                
                # 3. Recalcular totales de FortnightSummary
                self.stdout.write('🧮 Recalculando totales de FortnightSummary...')
                summaries_updated = self.recalculate_fortnight_summaries(migration_log)
                
                # 4. Asignar ventas huérfanas
                self.stdout.write('🔗 Asignando ventas a FortnightSummary...')
                sales_assigned = self.assign_orphan_sales(migration_log)

                migration_log['stats'] = {
                    'earnings_fixed': earnings_fixed,
                    'periods_migrated': periods_migrated,
                    'summaries_updated': summaries_updated,
                    'sales_assigned': sales_assigned
                }

                if options['dry_run']:
                    self.stdout.write(self.style.WARNING('🔍 DRY RUN - No se aplicaron cambios'))
                    raise transaction.TransactionManagementError("Dry run rollback")
                elif options['commit']:
                    self.stdout.write(self.style.SUCCESS('✅ Migración completada exitosamente'))
                else:
                    self.stdout.write(self.style.ERROR('❌ Debe especificar --dry-run o --commit'))
                    raise transaction.TransactionManagementError("No action specified")

        except transaction.TransactionManagementError:
            pass  # Expected for dry-run
        except Exception as e:
            migration_log['errors'].append(str(e))
            self.stdout.write(self.style.ERROR(f'❌ Error: {str(e)}'))

        # Guardar log
        with open(log_file, 'w') as f:
            json.dump(migration_log, f, indent=2, default=str)
        
        self.stdout.write(f'📄 Log guardado en: {log_file}')

    def fix_earnings_without_fortnight(self, log):
        """Corregir Earnings sin year/fortnight"""
        earnings_without_fortnight = Earning.objects.filter(
            fortnight_year__isnull=True
        ) | Earning.objects.filter(
            fortnight_number__isnull=True
        )
        
        count = 0
        for earning in earnings_without_fortnight:
            if earning.date_earned:
                year, fortnight = Earning.calculate_fortnight(earning.date_earned)
                earning.fortnight_year = year
                earning.fortnight_number = fortnight
                earning.save()
                count += 1
                
                log['changes'].append({
                    'type': 'earning_fixed',
                    'earning_id': earning.id,
                    'date_earned': earning.date_earned,
                    'year': year,
                    'fortnight': fortnight
                })
        
        return count

    def migrate_period_summaries(self, log):
        """Migrar PeriodSummary a FortnightSummary"""
        period_summaries = PeriodSummary.objects.filter(frequency='biweekly')
        count = 0
        
        for period in period_summaries:
            # Calcular year/fortnight desde period_start
            year, fortnight = Earning.calculate_fortnight(period.period_start)
            
            # Crear o actualizar FortnightSummary
            fortnight_summary, created = FortnightSummary.objects.get_or_create(
                employee=period.employee,
                fortnight_year=year,
                fortnight_number=fortnight,
                defaults={
                    'total_earnings': period.total_earnings,
                    'total_services': period.total_services,
                    'is_paid': period.is_paid,
                    'paid_at': period.paid_at,
                    'paid_by': period.paid_by,
                    'closed_at': period.closed_at,
                    'payment_method': period.payment_method,
                    'amount_paid': period.amount_paid,
                    'payment_reference': period.payment_reference,
                    'payment_notes': period.payment_notes
                }
            )
            
            if not created:
                # Actualizar con datos más recientes
                fortnight_summary.total_earnings = max(fortnight_summary.total_earnings, period.total_earnings)
                if period.is_paid and not fortnight_summary.is_paid:
                    fortnight_summary.is_paid = True
                    fortnight_summary.paid_at = period.paid_at
                    fortnight_summary.paid_by = period.paid_by
                fortnight_summary.save()
            
            count += 1
            log['changes'].append({
                'type': 'period_migrated',
                'period_id': period.id,
                'fortnight_summary_id': fortnight_summary.id,
                'created': created,
                'year': year,
                'fortnight': fortnight
            })
        
        return count

    def recalculate_fortnight_summaries(self, log):
        """Recalcular totales de FortnightSummary basado en Earnings reales"""
        from django.db.models import Sum, Count
        
        summaries = FortnightSummary.objects.all()
        count = 0
        
        for summary in summaries:
            # Calcular totales reales desde Earnings
            earnings_data = Earning.objects.filter(
                employee=summary.employee,
                fortnight_year=summary.fortnight_year,
                fortnight_number=summary.fortnight_number
            ).aggregate(
                total_amount=Sum('amount'),
                total_count=Count('id')
            )
            
            real_total = earnings_data['total_amount'] or 0
            real_count = earnings_data['total_count'] or 0
            
            if summary.total_earnings != real_total:
                old_total = summary.total_earnings
                summary.total_earnings = real_total
                summary.total_services = real_count
                summary.save()
                count += 1
                
                log['changes'].append({
                    'type': 'summary_recalculated',
                    'summary_id': summary.id,
                    'old_total': float(old_total),
                    'new_total': float(real_total),
                    'services': real_count
                })
        
        return count

    def assign_orphan_sales(self, log):
        """Asignar ventas sin período a FortnightSummary"""
        from apps.pos_api.models import Sale
        
        orphan_sales = Sale.objects.filter(
            period__isnull=True,
            employee__isnull=False,
            status='completed'
        )
        
        count = 0
        for sale in orphan_sales:
            # Calcular quincena de la venta
            year, fortnight = Earning.calculate_fortnight(sale.date_time.date())
            
            # Buscar FortnightSummary correspondiente
            try:
                summary = FortnightSummary.objects.get(
                    employee=sale.employee,
                    fortnight_year=year,
                    fortnight_number=fortnight
                )
                sale.period = summary
                sale.save()
                count += 1
                
                log['changes'].append({
                    'type': 'sale_assigned',
                    'sale_id': sale.id,
                    'summary_id': summary.id,
                    'year': year,
                    'fortnight': fortnight
                })
            except FortnightSummary.DoesNotExist:
                # Crear FortnightSummary si no existe
                summary = FortnightSummary.objects.create(
                    employee=sale.employee,
                    fortnight_year=year,
                    fortnight_number=fortnight,
                    total_earnings=0,
                    total_services=0
                )
                sale.period = summary
                sale.save()
                count += 1
                
                log['changes'].append({
                    'type': 'sale_assigned_new_summary',
                    'sale_id': sale.id,
                    'summary_id': summary.id,
                    'year': year,
                    'fortnight': fortnight
                })
        
        return count