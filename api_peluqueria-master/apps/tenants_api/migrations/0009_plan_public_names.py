from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tenants_api', '0008_alter_tenant_subscription_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tenant',
            name='plan_type',
            field=models.CharField(
                choices=[
                    ('free', 'Free'),
                    ('basic', 'Basic'),
                    ('premium', 'Business'),
                    ('enterprise', 'Enterprise'),
                    ('standard', 'Pro'),
                ],
                default='free',
                max_length=20,
            ),
        ),
    ]
