# Migration to clean duplicate periods before adding unique constraint

from django.db import migrations


def clean_duplicate_periods(apps, schema_editor):
    """Remove duplicate periods, keeping paid ones or oldest"""
    PayrollPeriod = apps.get_model('employees_api', 'PayrollPeriod')
    
    # Find all unique combinations
    from django.db.models import Count
    duplicates = PayrollPeriod.objects.values('employee', 'period_start', 'period_end').annotate(
        count=Count('id')
    ).filter(count__gt=1)
    
    for dup in duplicates:
        periods = PayrollPeriod.objects.filter(
            employee_id=dup['employee'],
            period_start=dup['period_start'],
            period_end=dup['period_end']
        ).order_by('created_at')
        
        # Keep paid period or first one
        keep = None
        for p in periods:
            if p.status == 'paid':
                keep = p
                break
        
        if not keep:
            keep = periods.first()
        
        # Delete others
        periods.exclude(id=keep.id).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0005_payrollperiod_approved_at_payrollperiod_approved_by_and_more'),
    ]

    operations = [
        migrations.RunPython(clean_duplicate_periods, reverse_code=migrations.RunPython.noop),
    ]
