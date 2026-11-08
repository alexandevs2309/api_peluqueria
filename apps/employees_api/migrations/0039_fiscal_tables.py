from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0038_alter_payrolldeduction_modified_by'),
    ]

    operations = [
        migrations.CreateModel(
            name='FiscalTable',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fiscal_year', models.IntegerField(help_text='Año fiscal')),
                ('effective_date', models.DateField(help_text='Fecha de vigencia')),
                ('exemption_annual', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('exemption_monthly', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('source', models.CharField(default='DGII', max_length=255)),
                ('version', models.IntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'ordering': ['-fiscal_year', '-effective_date', '-version']},
        ),
        migrations.CreateModel(
            name='FiscalBracket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('min_amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('max_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('rate', models.DecimalField(decimal_places=2, max_digits=5, help_text='Porcentaje')),
                ('base_amount', models.DecimalField(decimal_places=2, default=0, max_digits=12)),
                ('order', models.IntegerField(default=0)),
                ('fiscal_table', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='brackets', to='employees_api.fiscaltable')),
            ],
            options={'ordering': ['order', 'min_amount']},
        ),
        migrations.AlterUniqueTogether(
            name='fiscaltable',
            unique_together={('fiscal_year', 'version')},
        ),
    ]
