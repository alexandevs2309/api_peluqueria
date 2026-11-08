from django.db import migrations
from decimal import Decimal


def seed_fiscal_tables(apps, schema_editor):
    FiscalTable = apps.get_model('employees_api', 'FiscalTable')
    FiscalBracket = apps.get_model('employees_api', 'FiscalBracket')

    # Tabla 2026 (DGII)
    t2026, _ = FiscalTable.objects.get_or_create(
        fiscal_year=2026, version=1,
        defaults={
            'effective_date': __import__('datetime').date(2026, 1, 1),
            'exemption_annual': Decimal('416220.00'),
            'exemption_monthly': Decimal('34685.00'),
            'source': 'DGII',
        },
    )
    if t2026.brackets.count() == 0:
        FiscalBracket.objects.create(fiscal_table=t2026, min_amount=Decimal('0.00'), max_amount=Decimal('416220.00'), rate=Decimal('0.00'), base_amount=Decimal('0.00'), order=0)
        FiscalBracket.objects.create(fiscal_table=t2026, min_amount=Decimal('416220.01'), max_amount=Decimal('624329.00'), rate=Decimal('15.00'), base_amount=Decimal('0.00'), order=1)
        FiscalBracket.objects.create(fiscal_table=t2026, min_amount=Decimal('624329.01'), max_amount=Decimal('867123.00'), rate=Decimal('20.00'), base_amount=Decimal('31216.00'), order=2)
        FiscalBracket.objects.create(fiscal_table=t2026, min_amount=Decimal('867123.01'), max_amount=None, rate=Decimal('25.00'), base_amount=Decimal('79776.00'), order=3)

    # Tabla 2027 (Ley 30-26)
    t2027, _ = FiscalTable.objects.get_or_create(
        fiscal_year=2027, version=1,
        defaults={
            'effective_date': __import__('datetime').date(2027, 1, 1),
            'exemption_annual': Decimal('480000.00'),
            'exemption_monthly': Decimal('40000.00'),
            'source': 'DGII (Ley 30-26)',
        },
    )
    if t2027.brackets.count() == 0:
        FiscalBracket.objects.create(fiscal_table=t2027, min_amount=Decimal('0.00'), max_amount=Decimal('480000.00'), rate=Decimal('0.00'), base_amount=Decimal('0.00'), order=0)
        FiscalBracket.objects.create(fiscal_table=t2027, min_amount=Decimal('480000.01'), max_amount=Decimal('624329.00'), rate=Decimal('15.00'), base_amount=Decimal('0.00'), order=1)
        FiscalBracket.objects.create(fiscal_table=t2027, min_amount=Decimal('624329.01'), max_amount=Decimal('867123.00'), rate=Decimal('20.00'), base_amount=Decimal('31216.00'), order=2)
        FiscalBracket.objects.create(fiscal_table=t2027, min_amount=Decimal('867123.01'), max_amount=None, rate=Decimal('27.00'), base_amount=Decimal('79776.00'), order=3)


def reverse_seed(apps, schema_editor):
    FiscalTable = apps.get_model('employees_api', 'FiscalTable')
    FiscalTable.objects.filter(fiscal_year__in=[2026, 2027]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0039_fiscal_tables'),
    ]

    operations = [
        migrations.RunPython(seed_fiscal_tables, reverse_code=reverse_seed),
    ]
