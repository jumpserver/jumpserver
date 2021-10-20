from typing import Callable
import textwrap

from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.template.loader import render_to_string

from users.models import User
from common.utils import get_logger, reverse
from notifications.notifications import SystemMessage
from terminal.models import Session, Command
from notifications.models import SystemMsgSubscription
from notifications.backends import BACKEND
from orgs.utils import tmp_to_root_org
from common.utils import lazyproperty

logger = get_logger(__name__)

__all__ = ('CommandAlertMessage', 'CommandExecutionAlert')

CATEGORY = 'terminal'
CATEGORY_LABEL = _('Sessions')


class CommandAlertMixin:
    command: dict
    _get_message: Callable
    message_type_label: str

    @lazyproperty
    def subject(self):
        _input = self.command['input']
        if isinstance(_input, str):
            _input = _input.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

        subject = self.message_type_label + "%(cmd)s" % {
            'cmd': _input
        }
        return subject

    @classmethod
    def post_insert_to_db(cls, subscription: SystemMsgSubscription):
        """
        兼容操作，试图用 `settings.SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER` 的邮件地址
        assets_systemuser_assets找到用户，把用户设置为默认接收者
        """
        from settings.models import Setting
        db_setting = Setting.objects.filter(
            name='SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER'
        ).first()
        if db_setting:
            emails = db_setting.value
        else:
            emails = settings.SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER
        emails = emails.split(',')
        emails = [email.strip().strip('"') for email in emails]

        users = User.objects.filter(email__in=emails)
        if users:
            subscription.users.add(*users)
            subscription.receive_backends = [BACKEND.EMAIL]
            subscription.save()


class CommandAlertMessage(CommandAlertMixin, SystemMessage):
    category = CATEGORY
    category_label = CATEGORY_LABEL
    message_type_label = _('Danger command alert')

    def __init__(self, command):
        self.command = command

    @classmethod
    def gen_test_msg(cls):
        command = Command.objects.first().to_dict()
        return cls(command)

    def get_html_msg(self) -> dict:
        command = self.command

        with tmp_to_root_org():
            session = Session.objects.get(id=command['session'])
        session_detail_url = reverse(
            'api-terminal:session-detail', kwargs={'pk': command['session']},
            external=True, api_to_ui=True
        )
        context = {
            'command': command['input'],
            'hostname': command['asset'],
            'host_ip': session.asset_obj.ip,
            'user': command['user'],
            'risk_level': Command.get_risk_level_str(command['risk_level']),
            'session_detail_url': session_detail_url,
            'oid': session.org_id
        }
        message = render_to_string('terminal/_msg_command_alert.html', context)
        return {
            'subject': self.subject,
            'message': message
        }


class CommandExecutionAlert(CommandAlertMixin, SystemMessage):
    category = CATEGORY
    category_label = CATEGORY_LABEL
    message_type_label = _('Batch danger command alert')

    def __init__(self, command):
        self.command = command

    @classmethod
    def gen_test_msg(cls):
        from assets.models import Asset
        from users.models import User
        cmd = {
            'input': 'ifconfig eth0',
            'assets': Asset.objects.all()[:10],
            'user': str(User.objects.first()),
            'risk_level': 5,
        }
        return cls(cmd)

    def get_html_msg(self) -> dict:
        command = self.command
        _input = command['input']
        _input = _input.replace('\n', '<br>')

        assets = ', '.join([str(asset) for asset in command['assets']])
        context = {
            'command': _input,
            'assets': assets,
            'user': command['user'],
            'risk_level': Command.get_risk_level_str(command['risk_level'])
        }
        message = render_to_string('terminal/_msg_command_execue_alert.html', context)
        return {
            'subject': self.subject,
            'message': message
        }
