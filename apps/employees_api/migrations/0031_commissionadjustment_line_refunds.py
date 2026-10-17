from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0030_delete_employeeservice'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='commissionadjustment',
            name='sale_detail',
            field=models.ForeignKey(
                blank=True,
                help_text='Línea de venta origen (comisión por servicio)',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='commission_adjustments',
                to='pos_api.saledetail',
            ),
        ),
        migrations.AddField(
            model_name='commissionadjustment',
            name='idempotency_key',
            field=models.CharField(
                blank=True,
                help_text='Clave de idempotencia para reembolsos repetidos',
                max_length=64,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name='commissionadjustment',
            name='reason',
            field=models.CharField(
                choices=[
                    ('refund', 'Reembolso de venta'),
                    ('partial_refund', 'Reembolso parcial'),
                    ('bonus', 'Bono adicional'),
                    ('penalty', 'Penalización'),
                    ('correction', 'Corrección contable'),
                    ('other', 'Otro'),
                ],
                default='other',
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name='commissionadjustment',
            index=models.Index(
                fields=['sale_detail'],
                name='employees_a_sale_detai_6f0b2a_idx',
            ),
        ),
        migrations.RemoveConstraint(
            model_name='commissionadjustment',
            name='unique_refund_per_sale',
        ),
        migrations.AddConstraint(
            model_name='commissionadjustment',
            constraint=models.UniqueConstraint(
                condition=models.Q(('reason', 'refund')),
                fields=('sale', 'sale_detail', 'reason'),
                name='unique_refund_per_sale_line',
            ),
        ),
        migrations.AddConstraint(
            model_name='commissionadjustment',
            constraint=models.UniqueConstraint(
                condition=models.Q(('idempotency_key__isnull', False)),
                fields=('idempotency_key',),
                name='unique_adjustment_idempotency_key',
            ),
        ),
    ]
