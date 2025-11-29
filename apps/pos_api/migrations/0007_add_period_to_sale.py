# Migration for adding period field to Sale model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0001_initial'),
        ('pos_api', '0006_merge_20251122_0656'),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='period',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sales', to='employees_api.fortnightsummary'),
        ),
    ]