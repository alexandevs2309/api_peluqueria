import django; django.setup()
from django.apps import apps
for m in apps.get_models():
    if m.__name__ in ('UserRole', 'Role'):
        print(f'{m.__name__}: {m.__module__}')
        for f in m._meta.get_fields():
            print(f'  {f.name}: {type(f).__name__}')
