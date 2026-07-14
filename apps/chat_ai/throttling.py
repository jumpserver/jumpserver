from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import APIException
from rest_framework.throttling import SimpleRateThrottle

from chat_ai.models import AgentRun


class BackgroundTaskLimitExceeded(APIException):
    status_code = 429
    default_detail = 'Chat AI background task limit exceeded.'
    default_code = 'background_task_limit_exceeded'


class BackgroundTaskThrottle(SimpleRateThrottle):
    scope = 'chat_ai_background_task'

    def get_rate(self):
        return getattr(settings, 'CHAT_AI_BACKGROUND_TASK_RATE', '10/min')

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': request.user.pk,
        }


def _daily_usage(user_id):
    local_now = timezone.localtime()
    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)
    runs = AgentRun.objects.filter(
        user_id=user_id,
        date_created__gte=day_start,
        date_created__lt=day_end,
    )
    usage = runs.aggregate(
        input_tokens=Sum('input_tokens'),
        output_tokens=Sum('output_tokens'),
    )
    active_count = runs.filter(status__in=(
        AgentRun.Status.QUEUED,
        AgentRun.Status.RUNNING,
    )).count()
    actual_tokens = int(usage['input_tokens'] or 0) + int(usage['output_tokens'] or 0)
    return actual_tokens, active_count


def enforce_daily_token_limit(user_id):
    limit = int(getattr(settings, 'CHAT_AI_DAILY_TOKEN_LIMIT', 200000))
    if limit <= 0:
        return
    reservation = max(
        1, int(getattr(settings, 'CHAT_AI_BACKGROUND_TOKEN_RESERVATION', 8192))
    )
    actual_tokens, active_count = _daily_usage(user_id)
    projected_tokens = actual_tokens + (active_count + 1) * reservation
    if projected_tokens > limit:
        raise BackgroundTaskLimitExceeded(
            detail='The daily Chat AI token quota has been reached.',
            code='chat_ai_daily_token_limit',
        )


def enforce_background_enqueue_limits(user_id):
    maximum = max(
        1, int(getattr(settings, 'CHAT_AI_BACKGROUND_MAX_PENDING_PER_USER', 5))
    )
    pending_count = AgentRun.objects.filter(
        user_id=user_id,
        status__in=(AgentRun.Status.QUEUED, AgentRun.Status.RUNNING),
    ).count()
    if pending_count >= maximum:
        raise BackgroundTaskLimitExceeded(
            detail=f'No more than {maximum} Chat AI background tasks may be pending per user.',
            code='chat_ai_background_queue_limit',
        )
    enforce_daily_token_limit(user_id)


class TranscriptionThrottle(SimpleRateThrottle):
    scope = 'chat_ai_transcription'

    def get_rate(self):
        return getattr(settings, 'CHAT_AI_STT_RATE', '20/min')

    def get_cache_key(self, request, view):
        return self.cache_format % {
            'scope': self.scope,
            'ident': request.user.pk,
        }


class TranscriptionConcurrency:
    global_key = 'chat-ai:stt:concurrency:global'

    def __init__(self, user_id):
        self.user_key = f'chat-ai:stt:concurrency:user:{user_id}'
        self.acquired_keys = []
        self.ttl = max(60, getattr(settings, 'CHAT_AI_STT_TIMEOUT', 120) + 60)

    def _acquire_key(self, key, maximum):
        maximum = max(1, int(maximum))
        if cache.add(key, 1, self.ttl):
            self.acquired_keys.append(key)
            return True
        try:
            value = cache.incr(key)
        except ValueError:
            cache.set(key, 1, self.ttl)
            value = 1
        if value > maximum:
            try:
                cache.decr(key)
            except ValueError:
                pass
            return False
        self.acquired_keys.append(key)
        return True

    def acquire(self):
        global_maximum = getattr(settings, 'CHAT_AI_STT_GLOBAL_CONCURRENCY', 4)
        user_maximum = getattr(settings, 'CHAT_AI_STT_MAX_CONCURRENCY', 1)
        try:
            if not self._acquire_key(self.global_key, global_maximum):
                return False
            if not self._acquire_key(self.user_key, user_maximum):
                self.release()
                return False
        except Exception:
            self.release()
            raise
        return True

    def release(self):
        for key in reversed(self.acquired_keys):
            try:
                value = cache.decr(key)
                if value <= 0:
                    cache.delete(key)
            except ValueError:
                try:
                    cache.delete(key)
                except Exception:
                    pass
            except Exception:
                pass
        self.acquired_keys = []
