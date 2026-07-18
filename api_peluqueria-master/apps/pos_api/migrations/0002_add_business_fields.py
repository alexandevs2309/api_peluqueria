# Generated migration
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos_api', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='posconfiguration',
            name='business_name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name='posconfiguration',
            name='address',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='posconfiguration',
            name='phone',
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AddField(
            model_name='posconfiguration',
            name='email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AddField(
            model_name='posconfiguration',
            name='website',
            field=models.URLField(blank=True),
        ),
    ]
