import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings'); django.setup()
from django.urls import get_resolver
r = get_resolver()
for p in r.url_patterns:
    if str(p.pattern) == 'api/':
        for p2 in p.url_patterns:
            if 'tenant' in str(p2.pattern):
                print('Pattern:', p2.pattern)
                if hasattr(p2, 'url_patterns'):
                    for p3 in p2.url_patterns:
                        name = getattr(p3, 'name', None)
                        print(' ', p3.pattern, 'name=', name)
