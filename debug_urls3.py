import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings'); django.setup()
from django.urls import get_resolver
r = get_resolver()
for p in r.url_patterns:
    pp = str(p.pattern)
    print(pp, type(p).__name__)
    if hasattr(p, 'url_patterns'):
        for p2 in p.url_patterns:
            pp2 = str(p2.pattern)
            print(' ', pp2, type(p2).__name__)
            if hasattr(p2, 'url_patterns'):
                for p3 in p2.url_patterns:
                    pp3 = str(p3.pattern)
                    name = getattr(p3, 'name', 'N/A')
                    print('   ', pp3, 'name=', name)
            if hasattr(p2, 'callback'):
                print('   callback:', p2.callback)
                print('   name:', p2.name)
