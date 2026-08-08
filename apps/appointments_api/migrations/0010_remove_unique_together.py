from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('appointments_api', '0009_add_performance_indexes'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='appointment',
            unique_together=set(),
        ),
    ]
