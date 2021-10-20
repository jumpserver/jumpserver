from django.utils import timezone
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string

from notifications.notifications import UserMessage
from common.utils import get_logger

logger = get_logger(__file__)


class DifferentCityLoginMessage(UserMessage):
    def __init__(self, user, ip, city):
        self.ip = ip
        self.city = city
        super().__init__(user)

    def get_html_msg(self) -> dict:
        now = timezone.now().strftime("%Y-%m-%d %H:%M:%S")
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
