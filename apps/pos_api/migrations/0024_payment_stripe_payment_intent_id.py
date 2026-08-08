from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('pos_api', '0023_sale_points_earned_points_redeemed'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='stripe_payment_intent_id',
            field=models.CharField(blank=True, help_text='Stripe PaymentIntent ID for card payments', max_length=255, null=True),
        ),
    ]
