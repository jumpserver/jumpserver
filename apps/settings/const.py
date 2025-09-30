from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _


class ImportStatus(TextChoices):
    ok = 'ok', 'Ok'
    pending = 'pending', 'Pending'
    error = 'error', 'Error'


class ChatAIMethodChoices(TextChoices):
    api = 'api', 'API'
    embed = 'embed', _('Embed')


class ChatAITypeChoices(TextChoices):
    openai = 'openai', 'Openai'
    ollama = 'ollama', 'Ollama'
