from django.http import HttpResponseForbidden
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from apps.tenants_api.models import Tenant
from django.utils.deprecation import MiddlewareMixin

class TenantValidationMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated:
            return None

        # Extrae tenant de request (subdominio)
        host = request.META.get('HTTP_HOST', '').split(':')[0]
        request_tenant_subdomain = host.split('.')[0] if '.' in host else None

        if not request_tenant_subdomain:
            return HttpResponseForbidden("Tenant no detectado en subdominio.")

        try:
            # Valida token
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Bearer '):
                token = AccessToken(auth_header.split(' ')[1])
                token_tenant_id = token.get('tenant_id')
                token_tenant_subdomain = token.get('tenant_subdomain')

                if not token_tenant_subdomain or token_tenant_subdomain != request_tenant_subdomain:
                    return HttpResponseForbidden("Token no autorizado para este tenant.")

                # Opcional: Recarga tenant en request para views
                request.current_tenant = Tenant.objects.get(id=token_tenant_id)
            else:
                return HttpResponseForbidden("Token requerido.")
        except (InvalidToken, TokenError, Tenant.DoesNotExist):
            return HttpResponseForbidden("Token o tenant inválido.")

        return None