from rest_framework_simplejwt.tokens import AccessToken

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def get_user_agent(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    # Truncar a 255 caracteres para evitar error DataError
    return user_agent[:255] if user_agent else ''

def get_client_jti(token:str):
    try:
        token = AccessToken(token)
        return token.get('jti')
    except Exception as e:
        return None