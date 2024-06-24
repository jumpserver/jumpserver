from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from common.utils import get_logger
from common.utils.timezone import local_now_display
from notifications.notifications import UserMessage

logger = get_logger(__file__)


class LDAPImportMessage(UserMessage):
    def __init__(self, user, extra_kwargs):
        super().__init__(user)
        self.orgs = extra_kwargs.get('orgs', [])
        self.end_time = extra_kwargs.get('end_time', '')
        self.start_time = extra_kwargs.get('start_time', '')
        self.time_start_display = extra_kwargs.get('time_start_display', '')
        self.new_users = extra_kwargs.get('new_users', [])
        self.errors = extra_kwargs.get('errors', [])
        self.cost_time = extra_kwargs.get('cost_time', '')

    def get_html_msg(self) -> dict:
        subject = _('Notification of Synchronized LDAP User Task Results')
        context = {
            'orgs': self.orgs,
            'start_time': self.time_start_display,
            'end_time': local_now_display(),
            'cost_time': self.cost_time,
            'users': self.new_users,
            'errors': self.errors
        }
        message = render_to_string('ldap/_msg_import_ldap_user.html', context)
        return {
            'subject': subject,
            'message': message
        }
