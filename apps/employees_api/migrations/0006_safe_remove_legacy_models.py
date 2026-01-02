# Generated manually to safely remove legacy models

from django.db import migrations


def remove_legacy_models_if_exist(apps, schema_editor):
    """
    Elimina modelos legacy solo si existen en la base de datos.
    No intenta eliminar campos específicos para evitar errores.
    """
    db_alias = schema_editor.connection.alias
    
    # Lista de modelos a eliminar
    models_to_remove = [
        'employees_api_paymentreceipt',
        'employees_api_fortnightsummary', 
        'employees_api_payrollbatch',
        'employees_api_payrollbatchitem',
        'employees_api_periodsummary'
    ]
    
    # Verificar qué tablas existen en la base de datos (PostgreSQL)
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name LIKE 'employees_api_%'
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
    
        # Eliminar solo las tablas que realmente existen
        for table_name in models_to_remove:
            if table_name in existing_tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name} CASCADE")


def reverse_remove_legacy_models(apps, schema_editor):
    """
    No se puede revertir la eliminación de modelos legacy.
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('employees_api', '0005_remove_legacy_payroll_models'),
    ]

    operations = [
        migrations.RunPython(
            remove_legacy_models_if_exist,
            reverse_remove_legacy_models,
        ),
    ]