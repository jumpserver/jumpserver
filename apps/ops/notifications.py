from django.utils.translation import gettext_lazy as _

from notifications.notification import MessageBase


class ServerPerformance(MessageBase):
    message_label = _('Server performance')
