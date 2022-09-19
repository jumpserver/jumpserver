from django.db import models
from django.utils.translation import gettext_lazy as _

from common.db.models import IncludesTextChoicesMeta, ChoicesMixin



__all__ = [
    'Category', 'ConstrainMixin'
]



class Category(ConstrainMixin, ChoicesMixin, models.TextChoices):
    HOST = 'host', _('Host')
    DEVICE = 'device', _("Device")
    DATABASE = 'database', _("Database")
    CLOUD = 'cloud', _("Cloud service")
    WEB = 'web', _("Web")




