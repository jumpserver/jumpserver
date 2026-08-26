import sys
import threading

from django.apps import AppConfig
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class ChatAIConfig(AppConfig):
    name = 'chat_ai'
    verbose_name = _('Chat AI')

    def ready(self):
        from . import tasks  # noqa
        commands = {'migrate', 'makemigrations', 'check', 'collectstatic', 'compilemessages'}
        if not settings.CHAT_AI_ENABLED or not getattr(settings, 'CHAT_AI_SCHEMA_LOAD_ON_START', False):
            return
        if settings.ROOT_URLCONF != 'jumpserver.ai_urls':
            return
        if commands.intersection(sys.argv):
            return
        from common.signals import django_ready

        def start_loader(**kwargs):
            from .openapi import OpenAPILoader
            threading.Thread(
                target=OpenAPILoader()._load_sync,
                name='chat-ai-openapi-loader', daemon=True,
            ).start()

        django_ready.connect(start_loader, dispatch_uid='chat-ai-openapi-loader', weak=False)
