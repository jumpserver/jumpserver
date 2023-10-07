from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from assets.models import Asset
from audits.models import UserLoginLog
from notifications.notifications import UserMessage
from users.models import User


class UserLoginReminderMsg(UserMessage):
    subject = _('User login reminder')

    def __init__(self, user, user_log: UserLoginLog):
        self.user_log = user_log
        super().__init__(user)

    def get_html_msg(self) -> dict:
        user_log = self.user_log

        context = {
            'ip': user_log.ip,
            'city': user_log.city,
            'username': user_log.username,
            'recipient': self.user.username,
            'user_agent': user_log.user_agent,
        }
        message = render_to_string('acls/user_login_reminder.html', context)

        return {
            'subject': str(self.subject),
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        user = User.objects.first()
        user_log = UserLoginLog.objects.first()
        return cls(user, user_log)


class AssetLoginReminderMsg(UserMessage):
    subject = _('Asset login reminder')

    def __init__(self, user, asset: Asset, login_user: User):
        self.asset = asset
        self.login_user = login_user
        super().__init__(user)

    def get_html_msg(self) -> dict:
        context = {
            'recipient': self.user.username,
            'username': self.login_user.username,
            'asset': str(self.asset),
        }
        message = render_to_string('acls/asset_login_reminder.html', context)

        return {
            'subject': str(self.subject),
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        user = User.objects.first()
        asset = Asset.objects.first()
        return cls(user, asset, user)
