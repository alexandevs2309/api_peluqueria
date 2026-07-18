from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.billing_api.models import Invoice
from datetime import datetime, timedelta

User = get_user_model()

class Command(BaseCommand):
    help = 'Create sample invoices for testing'

    def handle(self, *args, **options):
        # Get or create test users
        user1, _ = User.objects.get_or_create(
            email='admin@test.com',
            defaults={'full_name': 'Admin Test'}
        )
        
        user2, _ = User.objects.get_or_create(
            email='client@test.com', 
            defaults={'full_name': 'Client Test'}
        )

        # Create sample invoices
        invoices = [
            {
                'user': user1,
                'amount': 49.99,
                'status': 'paid',
                'description': 'Professional Plan - January 2024',
                'due_date': datetime.now() - timedelta(days=5),
                'is_paid': True,
                'paid_at': datetime.now() - timedelta(days=3)
            },
            {
                'user': user2,
                'amount': 29.99,
                'status': 'pending',
                'description': 'Basic Plan - January 2024',
                'due_date': datetime.now() + timedelta(days=10),
                'is_paid': False
            },
            {
                'user': user1,
                'amount': 49.99,
                'status': 'pending',
                'description': 'Professional Plan - February 2024',
                'due_date': datetime.now() + timedelta(days=20),
                'is_paid': False
            }
        ]

        for invoice_data in invoices:
            Invoice.objects.get_or_create(
                user=invoice_data['user'],
                description=invoice_data['description'],
                defaults=invoice_data
            )

        self.stdout.write(
            self.style.SUCCESS('Successfully created sample invoices')
        )