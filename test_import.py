import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

try:
    from apps.employees_api.pending_payments_views import pending_payments
    print("✓ Import successful")
    print(f"Function: {pending_payments}")
except Exception as e:
    print(f"✗ Import failed: {e}")
    import traceback
    traceback.print_exc()
