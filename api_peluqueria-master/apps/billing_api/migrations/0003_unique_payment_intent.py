# Generated migration for unique payment_intent_id constraint

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing_api', '0002_add_reconciliation'),
    ]

    operations = [
        # Paso 1: Limpiar duplicados existentes (mantener el más reciente)
        migrations.RunSQL(
            sql="""
            WITH duplicates AS (
                SELECT id, stripe_payment_intent_id,
                       ROW_NUMBER() OVER (
                           PARTITION BY stripe_payment_intent_id 
                           ORDER BY paid_at DESC NULLS LAST, id DESC
                       ) as rn
                FROM billing_api_invoice
                WHERE stripe_payment_intent_id IS NOT NULL 
                  AND stripe_payment_intent_id != ''
            )
            UPDATE billing_api_invoice
            SET stripe_payment_intent_id = NULL
            WHERE id IN (
                SELECT id FROM duplicates WHERE rn > 1
            );
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
        
        # Paso 2: Convertir strings vacíos a NULL
        migrations.RunSQL(
            sql="""
            UPDATE billing_api_invoice 
            SET stripe_payment_intent_id = NULL 
            WHERE stripe_payment_intent_id = '';
            """,
            reverse_sql=migrations.RunSQL.noop
        ),
        
        # Paso 3: Modificar campo para permitir NULL
        migrations.AlterField(
            model_name='invoice',
            name='stripe_payment_intent_id',
            field=models.CharField(
                max_length=255, 
                blank=True, 
                null=True,
                db_index=True
            ),
        ),
        
        # Paso 4: Agregar constraint UNIQUE
        migrations.AlterField(
            model_name='invoice',
            name='stripe_payment_intent_id',
            field=models.CharField(
                max_length=255, 
                blank=True, 
                null=True,
                unique=True,
                db_index=True
            ),
        ),
    ]
