from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('employees_api', '0042_regalia_pascual'),
    ]

    operations = [
        migrations.CreateModel(
            name='Vacation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.IntegerField(help_text='Año al que corresponden las vacaciones')),
                ('days_entitled', models.IntegerField(default=0, help_text='Días de vacaciones correspondientes')),
                ('days_taken', models.IntegerField(default=0, help_text='Días disfrutados')),
                ('start_date', models.DateField(blank=True, null=True)),
                ('end_date', models.DateField(blank=True, null=True)),
                ('status', models.CharField(choices=[('pending', 'Pendiente'), ('enjoyed', 'Disfrutada'), ('compensated', 'Compensada')], default='pending', max_length=20)),
                ('paid_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('is_compensated', models.BooleanField(default=False)),
                ('compensated_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vacations', to='employees_api.employee')),
                ('compensated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='vacations_compensated', to=settings.AUTH_USER_MODEL)),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='vacations', to='tenants_api.tenant')),
            ],
            options={'ordering': ['-year']},
        ),
        migrations.AlterUniqueTogether(
            name='vacation',
            unique_together={('employee', 'year')},
        ),
    ]
