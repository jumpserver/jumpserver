import hashlib
import json
import threading
import time

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache

from common.utils import get_logger
from jumpserver.views.schema import CustomSchemaGenerator
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from .registry import OpenAPIRegistry

logger = get_logger(__name__)


class OpenAPILoader:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._lock = threading.Lock()
            cls._instance._registry = None
            cls._instance._schema_hash = ''
            cls._instance._loaded_at = 0.0
            cls._instance._loaded_wall_time = 0.0
        return cls._instance

    @property
    def schema_hash(self):
        return self._schema_hash

    @property
    def schema_version(self):
        return getattr(settings, 'VERSION', '')

    @staticmethod
    def _generate_schema():
        generator = CustomSchemaGenerator(urlconf='jumpserver.urls')
        request = Request(APIRequestFactory().get('/api/internal-chat-ai-schema'))
        return generator.get_schema(request=request, public=True)

    def _load_sync(self, force=False):
        ttl = getattr(settings, 'CHAT_AI_SCHEMA_CACHE_TTL', 3600)
        try:
            invalidated_at = float(cache.get('chat-ai:openapi:invalidated-at') or 0)
        except Exception:
            invalidated_at = 0
        if invalidated_at > self._loaded_wall_time:
            force = True
        if self._registry and not force and time.monotonic() - self._loaded_at < ttl:
            return self._registry
        with self._lock:
            if self._registry and not force and time.monotonic() - self._loaded_at < ttl:
                return self._registry
            try:
                schema = self._generate_schema()
                encoded = json.dumps(schema, sort_keys=True, ensure_ascii=False, default=str).encode()
                self._registry = OpenAPIRegistry(schema)
                self._schema_hash = hashlib.sha256(encoded).hexdigest()
                self._loaded_at = time.monotonic()
                self._loaded_wall_time = time.time()
                logger.info('Chat AI OpenAPI registry loaded: %s operations', len(self._registry))
            except Exception as exc:
                logger.warning('Chat AI OpenAPI registry load failed: %s', exc.__class__.__name__)
                if not self._registry:
                    self._registry = OpenAPIRegistry({'paths': {}})
            return self._registry

    async def load(self, force=False):
        return await sync_to_async(self._load_sync, thread_sensitive=True)(force)

    async def refresh(self):
        registry = await self.load(force=True)
        refreshed_at = time.time()
        self._loaded_wall_time = refreshed_at
        try:
            await sync_to_async(cache.set, thread_sensitive=True)(
                'chat-ai:openapi:invalidated-at', refreshed_at, timeout=None
            )
        except Exception:
            pass
        return registry
