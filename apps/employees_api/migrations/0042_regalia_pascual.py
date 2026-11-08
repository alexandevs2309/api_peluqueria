from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0041_employer_contributions'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegaliaPascual',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('year', models.IntegerField(help_text='Año fiscal al que corresponde')),
                ('ordinary_salary_annual', models.DecimalField(decimal_places=2, default=0, max_digits=12, help_text='Salario ordinario acumulado en el año (base + comisiones regulares)')),
                ('amount', models.DecimalField(decimal_places=2, default=0, max_digits=10, help_text='Importe de la regalía (1/12 del salario ordinario anual, con tope)')),
                ('is_tax_exempt', models.BooleanField(default=True, help_text='Exenta de ISR (Art. 222)')),
                ('status', models.CharField(choices=[('calculated', 'Calculada'), ('paid', 'Pagada')], default='calculated', max_length=20)),
                ('paid_at', models.DateTimeField(blank=True, null=True)),
                ('payment_reference', models.CharField(blank=True, max_length=100, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('employee', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='regalias_pascuales', to='employees_api.employee')),
                ('paid_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='regalias_paid', to='auth.User')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='regalias_pascuales', to='tenants_api.tenant')),
            ],
            options={'ordering': ['-year']},
        ),
        migrations.AlterUniqueTogether(
            name='regaliapascual',
            unique_together={('employee', 'year')},
        ),
    ]
