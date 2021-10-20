from django.utils import timezone
from django.utils.translation import ugettext as _

from notifications.notifications import UserMessage
from settings.api import PublicSettingApi
from common.utils import get_logger

logger = get_logger(__file__)

EMAIL_TEMPLATE = _(
    ""
    "<h3>{subject}</h3>"
    "<p>Dear {server_name} user, Hello!</p>"
    "<p>Your account has remote login behavior, please pay attention.</p>"
    "<p>User: {username}</p>"
    "<p>Login time: {time}</p>"
    "<p>Login location: {city} ({ip})</p>"
    "<p>If you suspect that the login behavior is abnormal, please modify "
    "<p>the account password in time.</p>"
    "<br>"
    "<p>Thank you for your attention to {server_name}!</p>")


class DifferentCityLoginMessage(UserMessage):
    def __init__(self, user, ip, city):
        self.ip = ip
        self.city = city
        super().__init__(user)

    @property
    def time(self):
        return timezone.now().strftime("%Y-%m-%d %H:%M:%S")

    @property
    def subject(self):
        return _('Different city login reminder')

    def get_text_msg(self) -> dict:
        message = _(
            ""
            "{subject}\n"
            "Dear {server_name} user, Hello!\n"
            "Your account has remote login behavior, please pay attention.\n"
            "User: {username}\n"
            "Login time: {time}\n"
            "Login location: {city} ({ip})\n"
            "If you suspect that the login behavior is abnormal, please modify "
            "the account password in time.\n"
            "Thank you for your attention to {server_name}!\n"
        ).format(
            subject=self.subject,
            server_name=PublicSettingApi.get_login_title(),
            username=self.user.username,
            ip=self.ip,
            time=self.time,
            city=self.city,
        )
        return {
            'subject': self.subject,
            'message': message
        }

    def get_html_msg(self) -> dict:
        message = EMAIL_TEMPLATE.format(
            subject=self.subject,
            server_name=PublicSettingApi.get_login_title(),
            username=self.user.username,
            ip=self.ip,
            time=self.time,
            city=self.city,
        )
        return {
            'subject': self.subject,
            'message': message
        }
