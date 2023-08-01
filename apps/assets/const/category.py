from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import ChoicesMixin

__all__ = ['Category']


class Category(ChoicesMixin, models.TextChoices):
    HOST = 'host', _('Host')
    DEVICE = 'device', _("Device")
    DATABASE = 'database', _("Database")
    CLOUD = 'cloud', _("Cloud service")
    WEB = 'web', _("Web")
    GPT = 'gpt', "GPT"
    CUSTOM = 'custom', _("Custom type")

    @classmethod
    def filter_choices(cls, category):
        _category = getattr(cls, category.upper(), None)
        choices = [(_category.value, _category.label)] if _category else cls.choices
        return choices
