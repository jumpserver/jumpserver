from django.utils.translation import gettext_lazy as _

from django.db.models import TextChoices


class SiteMessageDisplayMode(TextChoices):
    default = '', _('Default')
    popup = 'popup', _('Popup')

