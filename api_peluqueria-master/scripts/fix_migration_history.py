"""
Fix InconsistentMigrationHistory: inserts auth_api.0006 into django_migrations
directly via SQL, bypassing Django's migration loader consistency check.

Run before migrate:
    python scripts/fix_migration_history.py
"""
import os
import sys
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

django.setup()

from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'django_migrations'
        );
    """)
    table_exists = cursor.fetchone()[0]

    if not table_exists:
        print("[fix] django_migrations table does not exist yet — skipping.")
    else:
        cursor.execute(
            "SELECT COUNT(*) FROM django_migrations WHERE app = %s AND name = %s",
            ["auth_api", "0006_add_tenant_constraint_and_unique_email"],
        )
        exists = cursor.fetchone()[0]

        if exists:
            print("[fix] auth_api.0006 already in django_migrations — nothing to do.")
        else:
            cursor.execute(
                "INSERT INTO django_migrations (app, name, applied) VALUES (%s, %s, NOW())",
                ["auth_api", "0006_add_tenant_constraint_and_unique_email"],
            )
            print("[fix] Inserted auth_api.0006 into django_migrations OK.")
