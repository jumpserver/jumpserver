from django.utils.translation import gettext_lazy as _

from notifications.notifications import SystemMessage
from notifications.models import SystemMsgSubscription
from users.models import User
from notifications.backends import BACKEND

__all__ = ('ServerPerformanceMessage',)


class ServerPerformanceMessage(SystemMessage):
    category = 'Operations'
    category_label = _('Operations')
    message_type_label = _('Server performance')

    def __init__(self, path, usage):
        self.path = path
        self.usage = usage

    def get_common_msg(self):
        msg = _("Disk used more than 80%: {} => {}").format(self.path, self.usage.percent)
        return msg

    @classmethod
    def post_insert_to_db(cls, subscription: SystemMsgSubscription):
        admins = User.objects.filter(role=User.ROLE.ADMIN)
        subscription.users.add(*admins)
        subscription.receive_backends = [BACKEND.EMAIL]
        subscription.save()
