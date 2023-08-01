from django.template.loader import render_to_string
from django.utils.translation import gettext as _

from common.utils import get_logger
from common.utils.timezone import local_now_display
from notifications.notifications import UserMessage

logger = get_logger(__file__)


class DifferentCityLoginMessage(UserMessage):
    def __init__(self, user, ip, city):
        self.ip = ip
        self.city = city
        super().__init__(user)

    def get_html_msg(self) -> dict:
        now = local_now_display()
        subject = _('Different city login reminder')
        context = dict(
            subject=subject,
            name=self.user.name,
            username=self.user.username,
            ip=self.ip,
            time=now,
            city=self.city,
        )
        message = render_to_string('authentication/_msg_different_city.html', context)
        return {
            'subject': subject,
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
    def __init__(self, user, ip, oauth_name, oauth_id):
        super().__init__(user)
        self.ip = ip
        self.oauth_name = oauth_name
        self.oauth_id = oauth_id

    def get_html_msg(self) -> dict:
        now = local_now_display()
        subject = self.oauth_name + ' ' + _('binding reminder')
        context = dict(
            subject=subject,
            name=self.user.name,
            username=self.user.username,
            ip=self.ip,
            time=now,
            oauth_name=self.oauth_name,
            oauth_id=self.oauth_id
        )
        message = render_to_string('authentication/_msg_oauth_bind.html', context)
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
