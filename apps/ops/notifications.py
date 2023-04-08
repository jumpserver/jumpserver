from django.utils.translation import gettext_lazy as _
from django.utils.translation import gettext
from django.template.loader import render_to_string

from notifications.notifications import SystemMessage
from notifications.models import SystemMsgSubscription
from users.models import User
from notifications.backends import BACKEND
from terminal.models.component.status import Status
from terminal.models import Terminal

__all__ = ('ServerPerformanceMessage', 'ServerPerformanceCheckUtil')


class ServerPerformanceMessage(SystemMessage):
    category = 'Operations'
    category_label = _('App ops')
    message_type_label = _('Server performance')

    def __init__(self, terms_with_errors):
        self.terms_with_errors = terms_with_errors

    def get_html_msg(self) -> dict:
        subject = gettext("Terminal health check warning")
        context = {
            'terms_with_errors': self.terms_with_errors
        }
        message = render_to_string('ops/_msg_terminal_performance.html', context)
        return {
            'subject': subject,
            'message': message
        }

    @classmethod
    def post_insert_to_db(cls, subscription: SystemMsgSubscription):
        from rbac.models import Role, RoleBinding
        # Todo: 需要更改这里
        admin_role = Role.BuiltinRole.system_admin.get_role()
        admins_ids = RoleBinding.objects.filter(role=admin_role).values_list('user_id', flat=True)
        admins = User.objects.filter(id__in=admins_ids)
        subscription.users.add(*admins)
        subscription.receive_backends = [BACKEND.EMAIL]
        subscription.save()

    @classmethod
    def gen_test_msg(cls):
        from terminal.models import Terminal
        items_mapper = ServerPerformanceCheckUtil.items_mapper
        terms_with_errors = []
        terms = Terminal.objects.all()[:5]

        for i, term in enumerate(terms, 1):
            errors = []
            for item, data in items_mapper.items():
                msg = data['alarm_msg_format']
                max_threshold = data['max_threshold']
                value = 123 // i+1
                msg = msg.format(max_threshold=max_threshold, value=value, name=term.name)
                errors.append(msg)
            terms_with_errors.append([term, errors])
        return cls(terms_with_errors)


class ServerPerformanceCheckUtil(object):
    items_mapper = {
        'is_alive': {
            'default': False,
            'max_threshold': False,
            'alarm_msg_format': _('The terminal is offline: {name}')
        },
        'disk_used': {
            'default': 0,
            'max_threshold': 80,
            'alarm_msg_format': _('Disk used more than {max_threshold}%: => {value}')
        },
        'memory_used': {
            'default': 0,
            'max_threshold': 85,
            'alarm_msg_format': _('Memory used more than {max_threshold}%: => {value}'),
        },
        'cpu_load': {
            'default': 0,
            'max_threshold': 5,
            'alarm_msg_format': _('CPU load more than {max_threshold}: => {value}'),
        },
    }

    def __init__(self):
        self.terms_with_errors = []
        self._terminals = []

    def check_and_publish(self):
        self.check()
        self.publish()

    def check(self):
        self.terms_with_errors = []
        self.initial_terminals()

        for term in self._terminals:
            errors = self.check_terminal(term)
            if not errors:
                continue
            self.terms_with_errors.append((term, errors))

    def check_terminal(self, term):
        errors = []
        for item, data in self.items_mapper.items():
            error = self.check_item(term, item, data)
            if not error:
                continue
            errors.append(error)
        return errors

    @staticmethod
    def check_item(term, item, data):
        default = data['default']
        max_threshold = data['max_threshold']
        value = getattr(term.stat, item, default)

        if isinstance(value, bool) and value != max_threshold:
            return
        elif isinstance(value, (int, float)) and value < max_threshold:
            return
        msg = data['alarm_msg_format']
        error = msg.format(max_threshold=max_threshold, value=value, name=term.name)
        return error

    def publish(self):
        if not self.terms_with_errors:
            return
        ServerPerformanceMessage(self.terms_with_errors).publish()

    def initial_terminals(self):
        terminals = []
        for terminal in Terminal.objects.filter(is_deleted=False):
            if not terminal.is_active:
                continue
            terminal.stat = Status.get_terminal_latest_stat(terminal)
            terminals.append(terminal)
        self._terminals = terminals
