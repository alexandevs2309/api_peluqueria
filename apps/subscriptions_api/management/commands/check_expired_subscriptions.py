from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.subscriptions_api.models import UserSubscription
from apps.settings_api.policy_utils import should_auto_suspend_expired

class Command(BaseCommand):
    help = 'Check and deactivate expired subscriptions'

    def handle(self, *args, **options):
        if not should_auto_suspend_expired():
            self.stdout.write(
                self.style.WARNING('Auto suspension disabled in system settings; skipping expired subscriptions check')
            )
            return

        expired_subs = UserSubscription.objects.filter(
            is_active=True,
            end_date__lt=timezone.now()
        )
        
        count = expired_subs.count()
        expired_subs.update(is_active=False)
        
        self.stdout.write(
            self.style.SUCCESS(f'Deactivated {count} expired subscriptions')
        )
