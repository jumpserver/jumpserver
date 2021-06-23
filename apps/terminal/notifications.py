from django.utils.translation import gettext_lazy as _
from django.conf import settings

from users.models import User
from common.utils import get_logger, reverse
from notifications.notifications import SystemMessage
from terminal.models import Session, Command
from notifications.models import SystemMsgSubscription
from notifications.backends import BACKEND

logger = get_logger(__name__)

__all__ = ('CommandAlertMessage', 'CommandExecutionAlert')

CATEGORY = 'terminal'
CATEGORY_LABEL = _('Sessions')


class CommandAlertMixin:
    def get_dingtalk_msg(self) -> str:
        msg = self._get_message()
        msg = msg.replace('<br>', '')
        return msg

    @classmethod
    def post_insert_to_db(cls, subscription: SystemMsgSubscription):
        """
        兼容操作，试图用 `settings.SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER` 的邮件地址assets_systemuser_assets找到
        用户，把用户设置为默认接收者
        """
        from settings.models import Setting
        db_setting = Setting.objects.filter(name='SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER').first()
        if db_setting:
            emails = db_setting.value
        emails = emails or settings.SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER
        emails = emails.split(',')
        emails = [email.strip().strip('"') for email in emails]

        users = User.objects.filter(email__in=emails)
        subscription.users.add(*users)
        subscription.receive_backends = [BACKEND.EMAIL]
        subscription.save()


class CommandAlertMessage(CommandAlertMixin, SystemMessage):
    category = CATEGORY
    category_label = CATEGORY_LABEL
    message_type_label = _('Danger command alert')

    def __init__(self, command):
        self.command = command

    def _get_message(self):
        command = self.command
        session_obj = Session.objects.get(id=command['session'])

        message = _("""
                        Command: %(command)s
                        <br>
                        Asset: %(host_name)s (%(host_ip)s)
                        <br>
                        User: %(user)s
                        <br>
                        Level: %(risk_level)s
                        <br>
                        Session: <a href="%(session_detail_url)s">session detail</a>
                        <br>
                        """) % {
            'command': command['input'],
            'host_name': command['asset'],
            'host_ip': session_obj.asset_obj.ip,
            'user': command['user'],
            'risk_level': Command.get_risk_level_str(command['risk_level']),
            'session_detail_url': reverse('api-terminal:session-detail',
                                          kwargs={'pk': command['session']},
                                          external=True, api_to_ui=True),
        }

        return message

    def get_common_msg(self):
        return self._get_message()

    def get_email_msg(self):
        command = self.command
        session_obj = Session.objects.get(id=command['session'])

        input = command['input']
        if isinstance(input, str):
            input = input.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

        subject = _("Insecure Command Alert: [%(name)s->%(login_from)s@%(remote_addr)s] $%(command)s") % {
            'name': command['user'],
            'login_from': session_obj.get_login_from_display(),
            'remote_addr': session_obj.remote_addr,
            'command': input
        }

        message = self._get_message()

        return {
            'subject': subject,
            'message': message
        }


class CommandExecutionAlert(CommandAlertMixin, SystemMessage):
    category = CATEGORY
    category_label = CATEGORY_LABEL
    message_type_label = _('Batch danger command alert')

    def __init__(self, command):
        self.command = command

    def _get_message(self):
        command = self.command
        input = command['input']
        input = input.replace('\n', '<br>')

        assets = ', '.join([str(asset) for asset in command['assets']])
        message = _("""
                            Assets: %(assets)s
                            <br>
                            User: %(user)s
                            <br>
                            Level: %(risk_level)s
                            <br>

                            ----------------- Commands ---------------- <br>
                            %(command)s <br>
                            ----------------- Commands ---------------- <br>
                            """) % {
            'command': input,
            'assets': assets,
            'user': command['user'],
            'risk_level': Command.get_risk_level_str(command['risk_level']),
        }
        return message

    def get_common_msg(self):
        return self._get_message()

    def get_email_msg(self):
        command = self.command

        subject = _("Insecure Web Command Execution Alert: [%(name)s]") % {
            'name': command['user'],
        }
        message = self._get_message()

        return {
            'subject': subject,
            'message': message
        }
