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
        from rbac.models import Role, RoleBinding
        admin_role = Role.get_builtin_role(name=Role.admin_name, scope=Role.ScopeChoices.system)
        admins_ids = RoleBinding.objects.filter(role=admin_role).values_list('user_id', flat=True)
        admins = User.objects.filter(id__in=admins_ids)
        subscription.users.add(*admins)
        subscription.receive_backends = [BACKEND.EMAIL]
        subscription.save()
