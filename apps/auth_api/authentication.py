from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings

from apps.core.tenant_rls import rls_bypass


def _tenant_from_jwt_user(user):
    """Resuelve el tenant del JWT sin depender del RLS de la petición.

    En rutas públicas como ``/api/booking/<subdomain>/`` el contexto RLS se
    fija desde el subdomain de la URL, no desde el usuario autenticado. Acceder
    a ``user.tenant`` bajo ese contexto puede lanzar ``Tenant.DoesNotExist`` y
    convertir una página pública en un 500 cuando el visitante tiene cookie de
    otro negocio. El JWT ya trae ``tenant_id``: hacemos una única lectura
    explícita con bypass y devolvemos ``None`` si la fila ya no existe.
    """
    if getattr(user, 'is_superuser', False):
        return None

    tenant_id = getattr(user, 'tenant_id', None)
    if not tenant_id:
        return None

    from apps.tenants_api.models import Tenant

    with rls_bypass():
        return Tenant.objects.filter(pk=tenant_id).first()


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication que soporta tanto cookies httpOnly como Authorization header
    Esto permite migración gradual sin romper el desarrollo actual
    """

    @staticmethod
    def _attach_tenant(request, user):
        request.tenant = _tenant_from_jwt_user(user)

    def authenticate(self, request):
        # Primero intenta el método tradicional (Authorization header)
        header_auth = super().authenticate(request)
        if header_auth is not None:
            user, validated_token = header_auth
            self._attach_tenant(request, user)
            return header_auth
            
        # Si no hay header, intenta cookies
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None
            
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        self._attach_tenant(request, user)
        return (user, validated_token)


class DualJWTAuthentication(JWTAuthentication):
    """
    Autenticación que acepta AMBOS métodos simultáneamente
    Perfecto para desarrollo - no rompe nada existente
    """

    @staticmethod
    def _attach_tenant(request, user):
        request.tenant = _tenant_from_jwt_user(user)

    def authenticate(self, request):
        # Método 1: Authorization header (actual)
        try:
            header_auth = super().authenticate(request)
            if header_auth is not None:
                user, _ = header_auth
                self._attach_tenant(request, user)
                return header_auth
        except (InvalidToken, TokenError):
            pass
            
        # Método 2: httpOnly cookie (nuevo)
        try:
            raw_token = request.COOKIES.get('access_token')
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                user = self.get_user(validated_token)
                self._attach_tenant(request, user)
                return (user, validated_token)
        except (InvalidToken, TokenError):
            pass
            
        return None
