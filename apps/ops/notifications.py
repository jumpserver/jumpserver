from django.utils.translation import gettext_lazy as _

from notifications.notifications import SystemMessage
from notifications.models import SystemMsgSubscription
from users.models import User
from notifications.backends import BACKEND
from terminal.models import Status, Terminal

__all__ = ('ServerPerformanceMessage', 'ServerPerformanceCheckUtil')


class ServerPerformanceMessage(SystemMessage):
    category = 'Operations'
    category_label = _('Operations')
    message_type_label = _('Server performance')

    def __init__(self, msg):
        self._msg = msg

    def get_common_msg(self):
        return {
            'subject': self._msg[:80],
            'message': self._msg
        }

    @classmethod
    def post_insert_to_db(cls, subscription: SystemMsgSubscription):
        admins = User.objects.filter(role=User.ROLE.ADMIN)
        subscription.users.add(*admins)
        subscription.receive_backends = [BACKEND.EMAIL]
        subscription.save()


class ServerPerformanceCheckUtil(object):
    items_mapper = {
        'is_alive': {
            'default': False,
            'max_threshold': False,
            'alarm_msg_format': _('The terminal is offline: {name}')
        },
        'disk_usage': {
            'default': 0,
            'max_threshold': 80,
            'alarm_msg_format': _(
                '[Disk] Disk used more than {max_threshold}%: => {value} ({name})'
            )
        },
        'memory_usage': {
            'default': 0,
            'max_threshold': 85,
            'alarm_msg_format': _(
                '[Memory] Memory used more than {max_threshold}%: => {value} ({name})'
            ),
        },
        'cpu_load': {
            'default': 0,
            'max_threshold': 5,
            'alarm_msg_format': _(
                '[CPU] CPU load more than {max_threshold}: => {value} ({name})'
            ),
        },
    }

    def __init__(self):
        self.alarm_messages = []
        self._terminals = []
        self._terminal = None

    def check_and_publish(self):
        self.check()
        self.publish()

    def check(self):
        self.alarm_messages = []
        self.initial_terminals()
        for item, data in self.items_mapper.items():
            for self._terminal in self._terminals:
                self.check_item(item, data)

    def check_item(self, item, data):
        default = data['default']
        max_threshold = data['max_threshold']
        value = getattr(self._terminal.stat, item, default)
        print(value, max_threshold, self._terminal.name, self._terminal.id)
        if isinstance(value, bool) and value != max_threshold:
            return
        elif isinstance(value, (int, float)) and value < max_threshold:
            return
        msg = data['alarm_msg_format']
        msg = msg.format(max_threshold=max_threshold, value=value, name=self._terminal.name)
        self.alarm_messages.append(msg)

    def publish(self):
        if not self.alarm_messages:
            return
        msg = '<br>'.join(self.alarm_messages)
        ServerPerformanceMessage(msg).publish()

    def initial_terminals(self):
        terminals = []
        for terminal in Terminal.objects.filter(is_deleted=False):
            if not terminal.is_active:
                continue
            terminal.stat = Status.get_terminal_latest_stat(terminal)
            terminals.append(terminal)
        self._terminals = terminals
