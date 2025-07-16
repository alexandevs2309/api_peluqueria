from urllib import request
from django.utils.deprecation import MiddlewareMixin

class RoleDebugMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            roles = request.user.roles.values_list("name", flat=True)
            print(f"[DEBUG] {request.path} - Usuario {request.user.email} tiene roles: {list(roles)}")