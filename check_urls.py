import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
django.setup()

from django.urls import get_resolver

resolver = get_resolver()
patterns = resolver.url_patterns

def show_urls(patterns, prefix=''):
    for pattern in patterns:
        if hasattr(pattern, 'url_patterns'):
            show_urls(pattern.url_patterns, prefix + str(pattern.pattern))
        else:
            if 'pending' in str(pattern.pattern) or 'employees' in str(pattern.pattern):
                print(f"{prefix}{pattern.pattern}")

show_urls(patterns)
