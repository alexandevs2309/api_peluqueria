from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pos_api', '0015_alter_sale_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='posconfiguration',
            name='rnc',
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
