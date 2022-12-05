from common.exceptions import JMSException
from django.utils.translation import gettext_lazy as _


class PlaybookNoValidEntry(JMSException):
    default_detail = _('no valid program entry found.')
