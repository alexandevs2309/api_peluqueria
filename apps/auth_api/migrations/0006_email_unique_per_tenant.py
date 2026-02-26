# Generated migration for email unique per tenant

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_api', '0006_add_tenant_constraint'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='email',
            field=models.EmailField(max_length=255),
        ),
        migrations.AlterUniqueTogether(
            name='user',
            unique_together={('email', 'tenant')},
        ),
    ]
