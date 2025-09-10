from django.utils.translation import gettext as _

from common.utils import get_logger
from common.utils.timezone import local_now_display
from common.views.template import custom_render_to_string
from notifications.notifications import UserMessage

logger = get_logger(__file__)


class DifferentCityLoginMessage(UserMessage):
    subject = _('Different city login reminder')
    template_name = 'authentication/_msg_different_city.html'
    contexts = [
        {"name": "city", "label": _('Login city'), "default": "北京"},
        {"name": "username", "label": _('User'), "default": "zhangsan"},
        {"name": "name", "label": _('Name'), "default": "zhangsan"},
        {"name": "ip", "label": "IP", "default": "8.8.8.8"},
        {"name": "time", "label": _('Login Date'), "default": "2025-01-01 12:00:00"},
    ]

    def __init__(self, user, ip, city):
        self.ip = ip
        self.city = city
        super().__init__(user)

    def get_html_msg(self) -> dict:
        now = local_now_display()
        context = dict(
            name=self.user.name,
            username=self.user.username,
            ip=self.ip,
            time=now,
            city=self.city,
        )
        message = custom_render_to_string(self.template_name, context)
        return {
            'subject': self.subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        user = User.objects.first()
        ip = '8.8.8.8'
        city = '洛杉矶'
        return cls(user, ip, city)


class OAuthBindMessage(UserMessage):
    subject = _('OAuth binding reminder')
    template_name = 'authentication/_msg_oauth_bind.html'
    contexts = [
        {"name": "username", "label": _('User'), "default": "zhangsan"},
        {"name": "name", "label": _('Name'), "default": "zhangsan"},
        {"name": "ip", "label": "IP", "default": "8.8.8.8"},
        {"name": "oauth_name", "label": _('OAuth name'), "default": "WeCom"},
        {"name": "oauth_id", "label": _('OAuth ID'), "default": "000001"},
    ]

    def __init__(self, user, ip, oauth_name, oauth_id):
        super().__init__(user)
        self.ip = ip
        self.oauth_name = oauth_name
        self.oauth_id = oauth_id

    def get_html_msg(self) -> dict:
        now = local_now_display()
        subject = self.oauth_name + ' ' + _('binding reminder')
        context = dict(
            name=self.user.name,
            username=self.user.username,
            ip=self.ip,
            time=now,
            oauth_name=self.oauth_name,
            oauth_id=self.oauth_id
        )
        message = custom_render_to_string(self.template_name, context)
        return {
            'subject': subject,
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        user = User.objects.first()
        ip = '8.8.8.8'
        return cls(user, ip, _('WeCom'), '000000')
