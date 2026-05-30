import json
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import StreamingHttpResponse, HttpResponse

from .models import InAppNotification

logger = logging.getLogger(__name__)

REDIS_PUBSUB_CHANNEL_TPL = "notifications:user:{}"


_redis_url = None


def _get_redis_url():
    global _redis_url
    if _redis_url is None:
        _redis_url = settings.CACHES.get("default", {}).get("LOCATION", "redis://localhost:6379/0")
    return _redis_url


def publish_notification_event(user_id: int, event_data: dict) -> None:
    """
    Publica un evento de notificación en Redis PubSub para que el SSE
    lo entregue en tiempo real al usuario conectado.
    """
    try:
        import redis as sync_redis

        r = sync_redis.Redis.from_url(_get_redis_url())
        channel = REDIS_PUBSUB_CHANNEL_TPL.format(user_id)
        r.publish(channel, json.dumps(event_data))
        r.close()
    except Exception as exc:
        logger.warning("Redis PubSub publish failed for user %s: %s", user_id, exc)


def _get_unread_notifications(user):
    """Sync helper: retorna las notificaciones no leídas del usuario."""
    return list(
        InAppNotification.objects.filter(recipient=user, is_read=False)
        .order_by("-created_at")[:50]
        .values("id", "type", "title", "message", "is_read", "created_at")
    )


async def notification_sse(request):
    """
    SSE endpoint: GET /api/notifications/stream/
    Autentica por cookie httpOnly (JWT) o por query param ?token=<JWT>.

    Emite eventos:
      - event: init       → {unread_count, notifications[]}
      - event: notification → {id, type, title, message, is_read, created_at}
      - event: heartbeat   → mantiene conexión viva
    """
    from rest_framework_simplejwt.tokens import AccessToken
    from django.contrib.auth import get_user_model

    User = get_user_model()

    user = None

    token_param = request.GET.get("token")
    if token_param:
        try:
            access = AccessToken(token_param)
            user = await User.objects.aget(id=access["user_id"])
        except Exception as exc:
            logger.warning("SSE token auth failed: %s", exc)

    if not user and hasattr(request, "user") and request.user.is_authenticated:
        user = request.user

    if not user or not user.is_authenticated:
        return HttpResponse(status=401)

    async def event_stream():
        import asyncio
        import redis.asyncio as aioredis

        channel = REDIS_PUBSUB_CHANNEL_TPL.format(user.id)

        r = aioredis.Redis.from_url(_get_redis_url())
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)

        try:
            notifications = await sync_to_async(_get_unread_notifications)(user)
            init_payload = {
                "unread_count": len(notifications),
                "notifications": notifications,
            }
            yield f"event: init\ndata: {json.dumps(init_payload)}\n\n"

            while True:
                try:
                    message = await pubsub.get_message(
                        timeout=30.0, ignore_subscribe_messages=True
                    )
                    if message and message.get("type") == "message":
                        data = json.loads(message["data"])
                        event_type = data.pop("type", "notification")
                        yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                    else:
                        yield ": heartbeat\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                except Exception as exc:
                    logger.error("SSE stream error for user %s: %s", user.id, exc)
                    break
        except GeneratorExit:
            pass
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()
            await r.close()

    response = StreamingHttpResponse(
        event_stream(), content_type="text/event-stream"
    )
    response.is_async = True
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["Connection"] = "keep-alive"
    return response
