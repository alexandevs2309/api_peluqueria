from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients_api', '0004_alter_client_user'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['tenant', 'full_name'], name='clients_cl_tenant__f1a5a3_idx'),
        ),
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['tenant', 'branch'], name='clients_cl_tenant__b8c7d2_idx'),
        ),
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['tenant', 'is_active'], name='clients_cl_tenant__a3e1f9_idx'),
        ),
        migrations.AddIndex(
            model_name='client',
            index=models.Index(fields=['tenant', 'birthday'], name='clients_cl_tenant__c9d2e1_idx'),
        ),
    ]
