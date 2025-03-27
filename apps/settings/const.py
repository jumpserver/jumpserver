from django.db.models import TextChoices


class ImportStatus(TextChoices):
    ok = 'ok', 'Ok'
    pending = 'pending', 'Pending'
    error = 'error', 'Error'


class ChatAITypeChoices(TextChoices):
    gpt = 'gpt', 'GPT'
    deep_seek = 'deep-seek', 'DeepSeek'


class GPTModelChoices(TextChoices):
    gpt_4o_mini = 'gpt-4o-mini', 'gpt-4o-mini'
    gpt_4o = 'gpt-4o', 'gpt-4o'
    o3_mini = 'o3-mini', 'o3-mini'
    o1_mini = 'o1-mini', 'o1-mini'
    o1 = 'o1', 'o1'


class DeepSeekModelChoices(TextChoices):
    deepseek_chat = 'deepseek-chat', 'DeepSeek-V3'
    deepseek_reasoner = 'deepseek-reasoner', 'DeepSeek-R1'
