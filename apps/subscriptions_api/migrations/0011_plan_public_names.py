from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('subscriptions_api', '0010_subscriptionplan_is_public'),
    ]

    operations = [
        migrations.AlterField(
            model_name='subscriptionplan',
            name='name',
            field=models.CharField(
                choices=[
                    ('basic', 'Basic'),
                    ('standard', 'Pro'),
                    ('premium', 'Business'),
                    ('enterprise', 'Enterprise'),
                ],
                help_text='Name of the subscription plan',
                max_length=100,
                unique=True,
            ),
        ),
    ]
