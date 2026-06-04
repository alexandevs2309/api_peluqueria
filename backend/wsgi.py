import os
import traceback
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

_wsgi_error = None
try:
    from django.core.wsgi import get_wsgi_application
    application = get_wsgi_application()
except Exception:
    _wsgi_error = traceback.format_exc()
    print(_wsgi_error, file=sys.stderr, flush=True)

if _wsgi_error:
    def application(environ, start_response):
        start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
        return [f'Django startup failed\n{_wsgi_error}'.encode()]
