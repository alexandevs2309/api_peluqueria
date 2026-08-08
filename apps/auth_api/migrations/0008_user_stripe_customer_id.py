from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_api', '0007_user_avatar'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='stripe_customer_id',
            field=models.CharField(blank=True, db_index=True, max_length=255, null=True),
        ),
    ]
