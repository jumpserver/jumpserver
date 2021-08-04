from django.utils.translation import gettext_lazy as _
from django.conf import settings

from notifications.notifications import SystemMessage
from notifications.models import SystemMsgSubscription
from users.models import User
from notifications.backends import BACKEND
from common.utils import get_disk_usage, get_cpu_load, get_memory_used
from terminal.models import Status, Terminal

__all__ = ('ServerPerformanceMessage', 'ServerPerformanceCheckUtil')


class ServerPerformanceMessage(SystemMessage):
    category = 'Operations'
    category_label = _('Operations')
    message_type_label = _('Server performance')

    def __init__(self, msg):
        self._msg = msg

    def get_common_msg(self):
        return self._msg

    @classmethod
    def post_insert_to_db(cls, subscription: SystemMsgSubscription):
        from rbac.models import Role, RoleBinding
        # Todo: 需要更改这里
        admin_role = Role.get_builtin_role(name=Role.system_admin_name, scope=Role.Scope.system)
        admins_ids = RoleBinding.objects.filter(role=admin_role).values_list('user_id', flat=True)
        admins = User.objects.filter(id__in=admins_ids)
        subscription.users.add(*admins)
        subscription.receive_backends = [BACKEND.EMAIL]
        subscription.save()


class ServerPerformanceCheckUtil(object):

    def __init__(self):
        self.alarm_messages = []
        self.disk_usage_threshold = 20  # 80
        self.cpu_load_threshold = 1  # 5
        self.memory_usage_threshold = 20  # 85
        # checking terminal
        self._terminal = None

    def check_and_publish(self):
        self.check()
        self.publish()

    def publish(self):
        if not self.alarm_messages:
            return
        msg = '<br>'.join(self.alarm_messages)
        ServerPerformanceMessage(msg).publish()

    def check(self):
        check_items = ['disk_usage', 'cpu_load', 'memory_usage']

        # Check local
        if settings.DISK_CHECK_ENABLED:
            self.check_items(check_items)

        # Check terminal
        check_items += ['is_alive']
        terminals = self.get_terminals()
        for terminal in terminals:
            self._terminal = terminal
            self.check_items(check_items)

    @staticmethod
    def get_terminals():
        terminals = []
        for terminal in Terminal.objects.filter(is_accepted=True, is_deleted=False):
            if not terminal.is_active:
                continue
            terminal.status = Status.get_terminal_latest_stat(terminal)
            terminals.append(terminal)
        return terminals

    def check_items(self, items):
        for item in items:
            messages = getattr(self, f'check_{item}', lambda: None)()
            self.alarm_messages.extend(messages)

    def check_is_alive(self):
        message = []
        if not self._terminal and not self._terminal.is_alive:
            name = self._terminal.name
            msg = _('The terminal is offline: {}').format(name)
            message.append(msg)
        return message

    def check_disk_usage(self):
        messages = []
        if self._terminal:
            name = self._terminal.name
            disk_used = getattr(self._terminal.status, 'disk_used', None)
            disks_used = [['/', disk_used]] if disk_used else []
        else:
            name = 'Core'
            disks_used = self._get_local_disk_usage()

        for disk, used in disks_used:
            if used <= self.disk_usage_threshold:
                continue
            msg = _("Disk used more than {}%: {} => {} ({})").format(self.disk_usage_threshold, disk, used, name)
            messages.append(msg)
        return messages

    @staticmethod
    def _get_local_disk_usage():
        disks_usage = []
        usages = get_disk_usage()
        uncheck_paths = ['/etc', '/boot']
        for path, usage in usages.items():
            if len(path) > 4 and path[:4] in uncheck_paths:
                continue
            disks_usage.append([path, usage.percent])
        return disks_usage

    def check_cpu_load(self):
        messages = []
        if self._terminal:
            name = self._terminal.name
            cpu_load = getattr(self._terminal.status, 'cpu_load', 0)
        else:
            name = 'Core'
            cpu_load = get_cpu_load()

        if cpu_load > self.cpu_load_threshold:
            msg = _('CPU load more than {}: => {} ({})').format(self.cpu_load_threshold, cpu_load, name)
            messages.append(msg)
        return messages

    def check_memory_usage(self):
        messages = []
        if self._terminal:
            name = self._terminal.name
            memory_usage = getattr(self._terminal.status, 'memory_usage', 0)
        else:
            name = 'Core'
            memory_usage = get_memory_used()

        if memory_usage > self.memory_usage_threshold:
            msg = _('Memory used more than {}%: => {} ({})').format(self.memory_usage_threshold, memory_usage, name)
            messages.append(msg)
        return messages
