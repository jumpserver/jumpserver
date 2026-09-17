from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class ChatAIConfig(AppConfig):
    name = 'chat_ai'
    verbose_name = _('Chat AI')
