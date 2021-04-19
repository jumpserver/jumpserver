from django.utils.translation import gettext_lazy as _

from common.utils import get_logger, reverse
from notifications.notification import NoteBase
from terminal.models import Session, Command

logger = get_logger(__name__)


class CommandAlertNote(NoteBase):
    def get_common_msg(self, command):
        session_obj = Session.objects.get(id=command['session'])

        input = command['input']
        if isinstance(input, str):
            input = input.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

        msg = _("Insecure Command Alert: [%(name)s->%(login_from)s@%(remote_addr)s] $%(command)s") % {
            'name': command['user'],
            'login_from': session_obj.get_login_from_display(),
            'remote_addr': session_obj.remote_addr,
            'command': input
        }
        return msg

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

        logger.debug(message)
        return {
            'subject': subject,
            'message': message
        }
