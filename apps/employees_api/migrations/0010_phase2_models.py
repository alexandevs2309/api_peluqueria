from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
from decimal import Decimal

class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0009_add_payment_indexes'),
    ]

    operations = [
        # AdvanceLoan model
        migrations.CreateModel(
            name='AdvanceLoan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('loan_type', models.CharField(choices=[('advance', 'Anticipo de Sueldo'), ('personal_loan', 'Préstamo Personal'), ('emergency', 'Préstamo de Emergencia')], max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))])),
                ('reason', models.TextField()),
                ('status', models.CharField(choices=[('pending', 'Pendiente'), ('approved', 'Aprobado'), ('rejected', 'Rechazado'), ('active', 'Activo'), ('completed', 'Completado'), ('cancelled', 'Cancelado')], default='pending', max_length=20)),
                ('installments', models.IntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)])),
                ('interest_rate', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('request_date', models.DateField(auto_now_add=True)),
                ('approval_date', models.DateField(blank=True, null=True)),
                ('first_payment_date', models.DateField(blank=True, null=True)),
                ('approval_notes', models.TextField(blank=True)),
                ('total_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('monthly_payment', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('remaining_balance', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        
        # LoanPayment model
        migrations.CreateModel(
            name='LoanPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_date', models.DateField()),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('payment_number', models.IntegerField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['payment_number'],
            },
        ),
        
        # AccountingEntry model
        migrations.CreateModel(
            name='AccountingEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entry_type', models.CharField(choices=[('payroll', 'Nómina'), ('tax_provision', 'Provisión Impuestos'), ('loan_disbursement', 'Desembolso Préstamo'), ('loan_payment', 'Pago Préstamo')], max_length=20)),
                ('reference_id', models.CharField(max_length=50)),
                ('entry_date', models.DateField()),
                ('description', models.TextField()),
                ('debit_account', models.CharField(max_length=20)),
                ('credit_account', models.CharField(max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('tenant', models.CharField(max_length=100)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('exported', models.BooleanField(default=False)),
                ('export_date', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'ordering': ['-entry_date', '-created_at'],
            },
        ),
        
        # Add loan_deductions field to FortnightSummary
        migrations.AddField(
            model_name='fortnightsummary',
            name='loan_deductions',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]