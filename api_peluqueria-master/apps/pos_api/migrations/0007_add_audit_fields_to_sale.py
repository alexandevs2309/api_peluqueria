# Generated migration for adding audit fields to Sale model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pos_api', '0006_add_salerefund_model'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='sale',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sales_created',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='sale',
            name='updated_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='sales_updated',
                to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='sale',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='sale',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
        migrations.AddIndex(
            model_name='sale',
            index=models.Index(fields=['created_at'], name='pos_api_sal_created_at_idx'),
        ),
        migrations.AddIndex(
            model_name='sale',
            index=models.Index(fields=['created_by'], name='pos_api_sal_created_by_idx'),
        ),
    ]
