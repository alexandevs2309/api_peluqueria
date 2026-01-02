import json
import redis
import time
from django.http import StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()

@csrf_exempt
def earnings_events_stream(request):
    """Endpoint SSE para eventos de earnings en tiempo real"""
    
    # Autenticación por token en query param para SSE
    token = request.GET.get('token')
    if not token:
        return StreamingHttpResponse(
            "data: {\"error\": \"Token requerido\"}\n\n",
            content_type='text/event-stream',
            status=401
        )
    
    try:
        token_obj = Token.objects.get(key=token)
        user = token_obj.user
    except Token.DoesNotExist:
        return StreamingHttpResponse(
            "data: {\"error\": \"Token inválido\"}\n\n",
            content_type='text/event-stream',
            status=401
        )
    
    def event_stream():
        # Conectar a Redis
        try:
            redis_client = redis.Redis.from_url(
                settings.CACHES['default']['LOCATION'],
                decode_responses=True
            )
            redis_client.ping()  # Verificar conexión
        except Exception as e:
            yield f"data: {{\"error\": \"Redis no disponible: {str(e)}\"}}\n\n"
            return
        
        # Canal específico del tenant del usuario
        if not user.tenant:
            yield f"data: {{\"error\": \"Usuario sin tenant\"}}\n\n"
            return
            
        channel = f"tenant_{user.tenant.id}_earnings"
        pubsub = redis_client.pubsub()
        
        try:
            pubsub.subscribe(channel)
            
            # Enviar evento inicial de conexión
            yield f"data: {json.dumps({'type': 'CONNECTED', 'message': 'Conectado a eventos de earnings'})}\n\n"
            
            # Mantener conexión viva
            while True:
                message = pubsub.get_message(timeout=30)
                if message:
                    if message['type'] == 'message':
                        # Reenviar evento al cliente
                        yield f"data: {message['data']}\n\n"
                else:
                    # Heartbeat cada 30 segundos
                    yield f"data: {json.dumps({'type': 'HEARTBEAT'})}\n\n"
                    
        except GeneratorExit:
            pass
        except Exception as e:
            yield f"data: {{\"error\": \"Error en stream: {str(e)}\"}}\n\n"
        finally:
            try:
                pubsub.unsubscribe(channel)
                pubsub.close()
            except:
                pass
    
    response = StreamingHttpResponse(
        event_stream(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Headers'] = 'Cache-Control'
    
    return response