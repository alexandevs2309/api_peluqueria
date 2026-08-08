# Generated migration for CommissionAdjustment

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0010_payrollperiod_is_finalized'),
        ('pos_api', '0009_sale_commission_amount_snapshot_and_more'),
        ('tenants_api', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CommissionAdjustment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, help_text='Monto del ajuste (negativo para deducciones)', max_digits=10)),
                ('reason', models.CharField(
                    choices=[
                        ('refund', 'Reembolso de venta'),
                        ('bonus', 'Bono adicional'),
                        ('penalty', 'Penalización'),
                        ('correction', 'Corrección contable'),
                        ('other', 'Otro')
                    ],
                    default='other',
                    max_length=20
                )),
                ('description', models.TextField(blank=True, help_text='Descripción detallada del ajuste')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='commission_adjustments_created',
                    to=settings.AUTH_USER_MODEL
                )),
                ('employee', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='commission_adjustments',
                    to='employees_api.employee'
                )),
                ('payroll_period', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='commission_adjustments',
                    to='employees_api.payrollperiod'
                )),
                ('sale', models.ForeignKey(
                    blank=True,
                    help_text='Venta relacionada (si aplica)',
                    null=True,
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='commission_adjustments',
                    to='pos_api.sale'
                )),
                ('tenant', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='commission_adjustments',
                    to='tenants_api.tenant'
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='commissionadjustment',
            index=models.Index(fields=['payroll_period', 'employee'], name='employees_a_payroll_idx'),
        ),
        migrations.AddIndex(
            model_name='commissionadjustment',
            index=models.Index(fields=['sale'], name='employees_a_sale_id_idx'),
        ),
        migrations.AddIndex(
            model_name='commissionadjustment',
            index=models.Index(fields=['tenant', 'created_at'], name='employees_a_tenant_idx'),
        ),
    ]
