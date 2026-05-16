import django, os
os.environ['DJANGO_SETTINGS_MODULE'] = 'backend.settings'
django.setup()
from django.urls import get_resolver
r = get_resolver()
p = r.url_patterns[2].url_patterns[10]  
print('tenants/ resolver:', type(p).__name__)
for p2 in p.url_patterns:
    print(' ', type(p2).__name__, str(p2.pattern))
    if hasattr(p2, 'url_patterns'):
        for p3 in p2.url_patterns:
            name = getattr(p3, 'name', 'N/A')
            print('    ', str(p3.pattern), 'name=', name)

