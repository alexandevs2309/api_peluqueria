# Generated migration for adding SaleRefund model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('pos_api', '0005_add_sale_status_immutability'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SaleRefund',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('refund_date', models.DateTimeField(default=django.utils.timezone.now)),
                ('reason', models.TextField(blank=True)),
                ('refund_amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('original_total', models.DecimalField(decimal_places=2, max_digits=10)),
                ('original_payment_method', models.CharField(max_length=50)),
                ('refunded_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='refunds_processed', to=settings.AUTH_USER_MODEL)),
                ('sale', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='refund', to='pos_api.sale')),
            ],
            options={
                'verbose_name': 'Sale Refund',
                'verbose_name_plural': 'Sale Refunds',
                'ordering': ['-refund_date'],
            },
        ),
        migrations.AddIndex(
            model_name='salerefund',
            index=models.Index(fields=['refund_date'], name='pos_api_sal_refund_date_idx'),
        ),
    ]
