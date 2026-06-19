from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Limpia entradas de caché de órdenes PayPal expiradas'

    CACHE_KEY_PATTERNS = [
        'paypal:subscription:order:*',
        'paypal:subscription:capture:*',
    ]

    def handle(self, *args, **options):
        cleaned = 0
        for pattern in self.CACHE_KEY_PATTERNS:
            try:
                keys = cache.keys(pattern)
                for key in keys:
                    cache.delete(key)
                    cleaned += 1
            except NotImplementedError:
                self.stdout.write(self.style.WARNING(
                    f'Cache backend does not support keys() — cannot cleanup {pattern}'
                ))
                return
            except Exception as exc:
                logger.exception('Error cleaning %s: %s', pattern, exc)

        self.stdout.write(self.style.SUCCESS(
            f'Cleaned {cleaned} stale PayPal cache entries'
        ))
