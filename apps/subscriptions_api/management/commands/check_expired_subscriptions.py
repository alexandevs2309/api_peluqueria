from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.subscriptions_api.models import UserSubscription

class Command(BaseCommand):
    help = 'Check and deactivate expired subscriptions'

    def handle(self, *args, **options):
        expired_subs = UserSubscription.objects.filter(
            is_active=True,
            end_date__lt=timezone.now()
        )
        
        count = expired_subs.count()
        expired_subs.update(is_active=False)
        
        self.stdout.write(
            self.style.SUCCESS(f'Deactivated {count} expired subscriptions')
        )