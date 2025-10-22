from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    """
    JWT Authentication que soporta tanto cookies httpOnly como Authorization header
    Esto permite migración gradual sin romper el desarrollo actual
    """
    
    def authenticate(self, request):
        # Primero intenta el método tradicional (Authorization header)
        header_auth = super().authenticate(request)
        if header_auth is not None:
            return header_auth
            
        # Si no hay header, intenta cookies
        raw_token = request.COOKIES.get('access_token')
        if raw_token is None:
            return None
            
        validated_token = self.get_validated_token(raw_token)
        user = self.get_user(validated_token)
        return (user, validated_token)


class DualJWTAuthentication(JWTAuthentication):
    """
    Autenticación que acepta AMBOS métodos simultáneamente
    Perfecto para desarrollo - no rompe nada existente
    """
    
    def authenticate(self, request):
        # Método 1: Authorization header (actual)
        try:
            header_auth = super().authenticate(request)
            if header_auth is not None:
                return header_auth
        except (InvalidToken, TokenError):
            pass
            
        # Método 2: httpOnly cookie (nuevo)
        try:
            raw_token = request.COOKIES.get('access_token')
            if raw_token is not None:
                validated_token = self.get_validated_token(raw_token)
                user = self.get_user(validated_token)
                return (user, validated_token)
        except (InvalidToken, TokenError):
            pass
            
        return None