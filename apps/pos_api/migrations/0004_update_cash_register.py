# Generated migration for cash register updates

from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ('pos_api', '0003_alter_promotion_conditions'),
    ]

    operations = [
        # Actualizar valores null a 0.00
        migrations.RunSQL(
            "UPDATE pos_api_cashregister SET initial_cash = 0.00 WHERE initial_cash IS NULL;",
            reverse_sql="-- No reverse needed"
        ),
        migrations.RunSQL(
            "UPDATE pos_api_cashregister SET final_cash = 0.00 WHERE final_cash IS NULL;",
            reverse_sql="-- No reverse needed"
        ),
        
        # Agregar índices para optimización
        migrations.AddIndex(
            model_name='cashregister',
            index=models.Index(fields=['user', 'opened_at'], name='pos_api_cas_user_id_opened_idx'),
        ),
        migrations.AddIndex(
            model_name='cashregister',
            index=models.Index(fields=['is_open'], name='pos_api_cas_is_open_idx'),
        ),
    ]