from django.test import TestCase
from django.urls import get_resolver

class ShowUrls(TestCase):
    def test_show(self):
        def show(patterns, prefix=''):
            for p in patterns:
                if hasattr(p, 'url_patterns'):
                    show(p.url_patterns, prefix + str(p.pattern))
                else:
                    name = getattr(p, 'name', None)
                    if name and 'payroll' in name:
                        print('URL:', prefix + str(p.pattern), 'name=', name)
        show(get_resolver().url_patterns)