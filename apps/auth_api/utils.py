from rest_framework_simplejwt.tokens import AccessToken

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0]
    return request.META.get('REMOTE_ADDR')

def get_user_agent(request):
    return request.META.get('HTTP_USER_AGENT', '')

def get_client_jti(token:str):
    try:
        token = AccessToken(token)
        return token.get('jti')
    except Exception as e:
        return None