from django.core.management.base import BaseCommand
import sentry_sdk

class Command(BaseCommand):
    help = 'Test Sentry error reporting'

    def handle(self, *args, **options):
        self.stdout.write('Testing Sentry error reporting...')
        
        try:
            # Generar error de prueba
            raise Exception("Test error for Sentry monitoring")
        except Exception as e:
            sentry_sdk.capture_exception(e)
            self.stdout.write(
                self.style.SUCCESS('✅ Test error sent to Sentry')
            )
        
        # Test de mensaje personalizado
        sentry_sdk.capture_message("Test message from Django management command")
        self.stdout.write(
            self.style.SUCCESS('✅ Test message sent to Sentry')
        )