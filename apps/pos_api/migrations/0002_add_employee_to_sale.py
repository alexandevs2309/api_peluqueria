# Generated migration for adding employee field to Sale model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0001_initial'),
        ('pos_api', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sale',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='sales', to='auth.User'),
        ),
        migrations.AddField(
            model_name='sale',
            name='employee',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='sales', to='employees_api.employee'),
        ),
    ]