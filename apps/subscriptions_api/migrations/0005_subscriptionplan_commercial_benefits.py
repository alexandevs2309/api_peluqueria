from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions_api', '0004_subscriptionplan_stripe_price_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='subscriptionplan',
            name='commercial_benefits',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
