from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0040_seed_fiscal_tables'),
    ]

    operations = [
        migrations.AddField(model_name='payrollperiod', name='employer_sfs', field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name='payrollperiod', name='employer_afp', field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name='payrollperiod', name='employer_srl', field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name='payrollperiod', name='employer_infotep', field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
        migrations.AddField(model_name='payrollperiod', name='employer_total', field=models.DecimalField(decimal_places=2, default=0, max_digits=10)),
    ]
