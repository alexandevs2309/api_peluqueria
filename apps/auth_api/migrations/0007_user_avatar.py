from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_api', '0006_email_unique_per_tenant'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='avatar',
            field=models.ImageField(blank=True, null=True, upload_to='users/avatars/'),
        ),
    ]
