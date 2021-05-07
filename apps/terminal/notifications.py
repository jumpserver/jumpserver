from django.utils.translation import gettext_lazy as _

from common.utils import get_logger, reverse
from notifications.notification import MessageBase
from terminal.models import Session, Command

logger = get_logger(__name__)


class CommandAlertMessage(MessageBase):
    message_label = _('Command Alert')

    def _get_message(self, command):
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

    def get_common_msg(self, command):
        return self._get_message(command)

    def get_email_msg(self, command):
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

        message = self._get_message(command)

        return {
            'subject': subject,
            'message': message
        }


class CommandExecutionAlert(MessageBase):
    message_label = _('Batch command alert')

    def _get_message(self, command):
        input = command['input']
        input = input.replace('\n', '<br>')

        assets = ', '.join([str(asset) for asset in command['assets']])
        message = _("""
                            <br>
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

    def get_common_msg(self, command):
        return self._get_message(command)

    def get_email_msg(self, command):
        subject = _("Insecure Web Command Execution Alert: [%(name)s]") % {
            'name': command['user'],
        }
        message = self._get_message(command)

        return {
            'subject': subject,
            'message': message
        }
