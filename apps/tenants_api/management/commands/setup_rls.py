"""
Management command para aplicar Row Level Security
python manage.py setup_rls
"""
from django.core.management.base import BaseCommand
from django.db import connection
import os

class Command(BaseCommand):
    help = 'Setup PostgreSQL Row Level Security'
    
    def handle(self, *args, **options):
        sql_file = os.path.join(
            os.path.dirname(__file__), 
            '..', '..', '..', '..', 'sql', 'enable_rls_direct.sql'
        )
        
        if not os.path.exists(sql_file):
            self.stdout.write(
                self.style.ERROR(f'SQL file not found: {sql_file}')
            )
            return
        
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        with connection.cursor() as cursor:
            try:
                cursor.execute(sql_content)
                self.stdout.write(
                    self.style.SUCCESS('Row Level Security enabled successfully')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error enabling RLS: {e}')
                )
                raise