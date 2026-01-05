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
    gpt = 'gpt', 'GPT'
    deep_seek = 'deep-seek', 'DeepSeek'


class GPTModelChoices(TextChoices):
    custom = 'custom', _('Custom gpt model')
    # 🚀 Latest flagship dialogue model
    GPT_5_2 = 'gpt-5.2', 'gpt-5.2'
    GPT_5_2_PRO = 'gpt-5.2-pro', 'gpt-5.2-pro'

    GPT_5_1 = 'gpt-5.1', 'gpt-5.1'
    GPT_5 = 'gpt-5', 'gpt-5'

    # 💡 Lightweight & Cost-Friendly Version
    GPT_5_MINI = 'gpt-5-mini', 'gpt-5-mini'
    GPT_5_NANO = 'gpt-5-nano', 'gpt-5-nano'

    # 🧠 GPT-4 series of dialogues (still supports chat tasks)
    GPT_4O = 'gpt-4o', 'gpt-4o'
    GPT_4O_MINI = 'gpt-4o-mini', 'gpt-4o-mini'
    GPT_4_1 = 'gpt-4.1', 'gpt-4.1'
    GPT_4_1_MINI = 'gpt-4.1-mini', 'gpt-4.1-mini'
    GPT_4_1_NANO = 'gpt-4.1-nano', 'gpt-4.1-nano'


class DeepSeekModelChoices(TextChoices):
    custom = 'custom', _('Custom DeepSeek model')
    deepseek_chat = 'deepseek-chat', 'DeepSeek-V3'
    deepseek_reasoner = 'deepseek-reasoner', 'DeepSeek-R1'
