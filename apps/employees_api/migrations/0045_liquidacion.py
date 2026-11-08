from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0044_vacation_corrections'),
    ]

    operations = [
        migrations.CreateModel(
            name='Liquidacion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('termination_date', models.DateField()),
                ('termination_type', models.CharField(choices=[('desahucio', 'Desahucio (sin causa)'), ('despido_causa', 'Despido con causa'), ('despido_sin_causa', 'Despido sin causa'), ('dimision_causa', 'Dimisión con causa'), ('dimision_sin_causa', 'Dimisión sin causa'), ('mutuo_acuerdo', 'Mutuo acuerdo')], max_length=20)),
                ('years_of_service', models.DecimalField(decimal_places=2, default=0, max_digits=6)),
                ('months_of_service', models.IntegerField(default=0)),
                ('daily_salary', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('preaviso_days', models.IntegerField(default=0)),
                ('preaviso_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('cesantia_days', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('cesantia_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('vacation_days', models.IntegerField(default=0)),
                ('vacation_amount', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('regalia_proporcional', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('participacion_beneficios', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('total', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('status', models.CharField(choices=[('calculated', 'Calculada'), ('paid', 'Pagada')], default='calculated', max_length=20)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('payment_reference', models.CharField(blank=True, max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='liquidaciones', to='employees_api.employee')),
                ('paid_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='liquidaciones_paid', to='auth.User')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='liquidaciones', to='tenants_api.tenant')),
            ],
            options={'ordering': ['-termination_date']},
        ),
    ]
