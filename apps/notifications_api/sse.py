import asyncio
import json
import logging
from datetime import datetime

import redis.asyncio as aioredis
from django.conf import settings
from django.http import StreamingHttpResponse, HttpResponse

from .models import InAppNotification

logger = logging.getLogger(__name__)

REDIS_PUBSUB_CHANNEL_TPL = "notifications:user:{}"
SSE_HEARTBEAT_INTERVAL = 30


_redis_url = None


def _get_redis_url():
    global _redis_url
    if _redis_url is None:
        _redis_url = settings.CACHES.get("default", {}).get(
            "LOCATION", "redis://localhost:6379/0"
        )
    return _redis_url


def publish_notification_event(user_id: int, event_data: dict) -> None:
    """Publica evento de notificación en Redis PubSub desde código síncrono."""
    try:
        import redis as sync_redis

        r = sync_redis.Redis.from_url(_get_redis_url())
        channel = REDIS_PUBSUB_CHANNEL_TPL.format(user_id)
        r.publish(channel, json.dumps(event_data))
        r.close()
    except Exception as exc:
        logger.warning("Redis PubSub publish failed for user %s: %s", user_id, exc)


async def _get_unread_notifications(user):
    from asgiref.sync import sync_to_async

    from .models import InAppNotification

    notifications = await sync_to_async(list)(
        InAppNotification.objects.filter(recipient=user, is_read=False)
        .order_by("-created_at")[:50]
        .values("id", "type", "title", "message", "is_read", "created_at")
    )
    for n in notifications:
        if isinstance(n.get("created_at"), datetime):
            n["created_at"] = n["created_at"].isoformat()
    return notifications


async def notification_sse(request):
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

    import os
    if os.environ.get("RUNNING_SSE") != "true":
        return HttpResponse("SSE is only supported under the dedicated ASGI server.", status=501)

    async def event_stream():
        channel = REDIS_PUBSUB_CHANNEL_TPL.format(user.id)

        r = aioredis.from_url(
            _get_redis_url(),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=None,
        )
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)

        try:
            notifications = await _get_unread_notifications(user)
            init_payload = {
                "unread_count": len(notifications),
                "notifications": notifications,
            }
            yield f"event: init\ndata: {json.dumps(init_payload)}\n\n"

            while True:
                try:
                    message = await pubsub.get_message(
                        timeout=SSE_HEARTBEAT_INTERVAL,
                        ignore_subscribe_messages=True,
                    )
                    if message and message.get("type") == "message":
                        data = json.loads(message["data"])
                        event_type = data.pop("type", "notification")
                        yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                    else:
                        yield ": heartbeat\n\n"
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
                except Exception:
                    logger.exception("SSE stream error for user %s", user.id)
                    break
        except GeneratorExit:
            pass
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.close()
                await r.close()
            except Exception:
                pass

    response = StreamingHttpResponse(
        event_stream(), content_type="text/event-stream"
    )
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    response["Connection"] = "keep-alive"
    return response
