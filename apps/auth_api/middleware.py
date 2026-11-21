from django.http import HttpResponseForbidden
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from apps.tenants_api.models import Tenant
from django.utils.deprecation import MiddlewareMixin

class CSRFProtectionMiddleware(MiddlewareMixin):
    """Protege endpoints mutantes cuando las cookies viajan con SameSite=None.

    Requiere ``X-Requested-With: XMLHttpRequest`` en POST/PUT/PATCH/DELETE.
    El frontend Angular lo envía en AuthInterceptor. No hay bypass por DEBUG,
    ``sys.argv`` ni por la presencia de pytest: el perfil productivo y el de
    tests se comportan igual. Las únicas exenciones son callbacks externos
    verificados por firma y formularios públicos sin sesión.
    """
    SAFE_METHODS = ('GET', 'HEAD', 'OPTIONS', 'TRACE')

    EXEMPT_PREFIXES = (
        # Django admin gestiona su propio CSRF.
        '/admin/',
        # Webhooks externos (firma verificada en la vista).
        '/api/billing/webhooks/stripe/',
        '/api/billing/webhooks/paypal/',
        '/api/payments/stripe/webhook/',
        '/api/payments/azul/webhook/',
        '/api/settings/barbershop/whatsapp_webhook/',
        # Telemetría anónima.
        '/api/telemetry/errors/',
        # Registro público y formularios sin sesión.
        '/api/subscriptions/register/',
        '/api/subscriptions/register-with-plan/',
        '/api/subscriptions/check-email/',
        '/api/settings/contact/',
        '/api/auth/register/',
        '/api/auth/reset-password/',
        '/api/auth/reset-password-confirm/',
        # Entradas de autenticidad pública; el resto de /api/auth/ exige header.
        '/api/auth/login/',
        '/api/auth/cookie-login/',
        '/api/auth/mfa/login-verify/',
    )

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method in self.SAFE_METHODS:
            return None

        if any(request.path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return None

        if request.META.get('HTTP_X_REQUESTED_WITH') != 'XMLHttpRequest':
            return HttpResponseForbidden("CSRF: falta header X-Requested-With.")

        return None


class TenantValidationMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if not request.user.is_authenticated:
            return None

        if getattr(request.user, 'is_superuser', False):
            return None

        try:
            # Valida token (desde header o cookie)
            token_str = None
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Bearer '):
                token_str = auth_header.split(' ')[1]
            else:
                token_str = request.COOKIES.get('access_token')

            if token_str:
                token = AccessToken(token_str)
                token_tenant_id = token.get('tenant_id')

                if not token_tenant_id or token_tenant_id != getattr(request.user, 'tenant_id', None):
                    return HttpResponseForbidden("Token no autorizado para este tenant.")

                # Opcional: Recarga tenant en request para views
                request.current_tenant = Tenant.objects.get(id=token_tenant_id)
            else:
                return HttpResponseForbidden("Token requerido.")
        except (InvalidToken, TokenError, Tenant.DoesNotExist):
            return HttpResponseForbidden("Token o tenant inválido.")

        return None
