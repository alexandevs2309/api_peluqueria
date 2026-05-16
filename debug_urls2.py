import django, os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings'); django.setup()
from django.urls import get_resolver
r = get_resolver()
for p in r.url_patterns:
    if str(p.pattern) == 'api/':
        print('api/ patterns:')
        for p2 in p.url_patterns:
            print(' ', str(p2.pattern), type(p2).__name__)
            if hasattr(p2, 'url_patterns'):
                for p3 in p2.url_patterns:
                    name = getattr(p3, 'name', 'N/A')
                    callback = getattr(p3, 'callback', 'N/A')
                    print('   ', str(p3.pattern), 'name=', name)
            if hasattr(p2, 'callback'):
                print('   callback:', p2.callback)
                print('   name:', p2.name)
