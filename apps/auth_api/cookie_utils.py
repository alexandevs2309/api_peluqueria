from __future__ import annotations

from typing import Optional

from django.conf import settings


def auth_cookie_samesite() -> str:
    # Cross-origin frontend/backend deployments require SameSite=None so
    # browsers will attach the JWT cookies on subsequent API requests.
    return 'Lax' if settings.DEBUG else 'None'


def auth_cookie_secure() -> bool:
    return not settings.DEBUG


def set_auth_cookies(
    response,
    *,
    access_token: str,
    refresh_token: Optional[str] = None,
    access_max_age: Optional[int] = None,
    refresh_max_age: Optional[int] = None,
    tenant_id: Optional[int] = None,
):
    cookie_secure = auth_cookie_secure()
    cookie_samesite = auth_cookie_samesite()

    response.set_cookie(
        'access_token',
        value=access_token,
        httponly=True,
        secure=cookie_secure,
        samesite=cookie_samesite,
        max_age=access_max_age,
        path='/',
    )

    if refresh_token is not None:
        response.set_cookie(
            'refresh_token',
            value=refresh_token,
            httponly=True,
            secure=cookie_secure,
            samesite=cookie_samesite,
            max_age=refresh_max_age,
            path='/',
        )

    if tenant_id is not None:
        response.set_cookie(
            'tenant_id',
            value=str(tenant_id),
            httponly=False,
            secure=cookie_secure,
            samesite=cookie_samesite,
            path='/',
        )

    return response


def clear_auth_cookies(response):
    cookie_secure = auth_cookie_secure()
    cookie_samesite = auth_cookie_samesite()

    response.delete_cookie('access_token', path='/', samesite=cookie_samesite)
    response.delete_cookie('refresh_token', path='/', samesite=cookie_samesite)
    response.delete_cookie('tenant_id', path='/', samesite=cookie_samesite)

    # Keep secure deletion aligned with production cookies for stricter browsers.
    response.cookies['access_token']['secure'] = cookie_secure
    response.cookies['refresh_token']['secure'] = cookie_secure
    response.cookies['tenant_id']['secure'] = cookie_secure

    return response
