from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ('pos_api', '0023_sale_points_earned_points_redeemed'),
        ('clients_api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoyaltyTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('points', models.PositiveIntegerField()),
                ('transaction_type', models.CharField(choices=[('earned', 'Earned'), ('redeemed', 'Redeemed')], max_length=10)),
                ('description', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='loyalty_transactions', to='clients_api.client')),
                ('sale', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='loyalty_transactions', to='pos_api.sale')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
