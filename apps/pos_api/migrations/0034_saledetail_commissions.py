from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    """
    Comisiones POR LÍNEA de venta.

    Migración estrictamente aditiva: solo agrega columnas opcionales e
    índices. NO modifica ni recalcula ninguna venta histórica, y los
    snapshots a nivel de venta existentes se conservan intactos.
    """

    dependencies = [
        ('employees_api', '0030_delete_employeeservice'),
        ('pos_api', '0033_cashregister_unique_open_register_per_user_branch_and_more'),
    ]

    operations = [
        # ── Línea de venta: barbero responsable + snapshots ──────────────
        migrations.AddField(
            model_name='saledetail',
            name='employee',
            field=models.ForeignKey(
                blank=True,
                help_text='Empleado/barbero responsable de esta línea',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sale_details',
                to='employees_api.employee',
            ),
        ),
        migrations.AddField(
            model_name='saledetail',
            name='commission_rate_snapshot',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Porcentaje de comisión vigente para esta línea al momento de la venta',
                max_digits=5,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='saledetail',
            name='commission_amount_snapshot',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Monto de comisión de esta línea al momento de la venta',
                max_digits=14,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name='saledetail',
            name='commission_source',
            field=models.CharField(
                blank=True,
                default='',
                help_text='Origen de la tasa: service|history|global|none',
                max_length=32,
            ),
        ),
        migrations.AddIndex(
            model_name='saledetail',
            index=models.Index(
                fields=['employee', 'commission_amount_snapshot'],
                name='pos_api_sale_employe_9c1d3f_idx',
            ),
        ),
        # ── Reembolsos parciales ────────────────────────────────────────
        migrations.AddField(
            model_name='sale',
            name='amount_refunded',
            field=models.DecimalField(
                decimal_places=2,
                default=0.00,
                help_text='Suma ya reembolsada; permite reembolsos parciales idempotentes',
                max_digits=14,
            ),
        ),
    ]
