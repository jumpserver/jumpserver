from django.utils.translation import gettext_lazy as _

from notifications.notification import MessageBase


class ServerPerformanceMessage(MessageBase):
    app_label = 'ops'
    message_label = _('Server performance')

    def get_common_msg(self, path, usage):
        msg = _("Disk used more than 80%: {} => {}").format(path, usage.percent)
        return msg
