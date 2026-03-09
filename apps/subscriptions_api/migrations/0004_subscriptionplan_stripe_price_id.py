from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions_api', '0003_alter_subscriptionplan_name'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptionplan',
            name='stripe_price_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Stripe Price ID (ej: price_...) para cobro recurrente',
                max_length=120,
                null=True
            ),
        ),
    ]

