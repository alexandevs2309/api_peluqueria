"""Minimal WSGI app - gunicorn startup test"""
def application(environ, start_response):
    start_response('200 OK', [('Content-Type', 'text/plain')])
    return [b'gunicorn test OK']
