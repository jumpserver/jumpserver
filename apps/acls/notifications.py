from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from accounts.models import Account
from acls.models import LoginACL, LoginAssetACL
from assets.models import Asset
from audits.models import UserLoginLog
from notifications.notifications import UserMessage
from users.models import User


class UserLoginReminderMsg(UserMessage):
    subject = _('User login reminder')

    def __init__(self, user, user_log: UserLoginLog, acl: LoginACL):
        self.user_log = user_log
        self.acl_name = str(acl)
        super().__init__(user)

    def get_html_msg(self) -> dict:
        user_log = self.user_log
        context = {
            'ip': user_log.ip,
            'city': user_log.city,
            'username': user_log.username,
            'recipient': self.user,
            'acl_name': self.acl_name,
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
    subject = _('User login alert for asset')

    def __init__(
            self, user, asset: Asset, login_user: User,
            account: Account, acl: LoginAssetACL,
            ip, input_username
    ):
        self.ip = ip
        self.asset = asset
        self.account = account
        self.acl_name = str(acl)
        self.login_user = login_user
        self.input_username = input_username
        super().__init__(user)

    def get_html_msg(self) -> dict:
        context = {
            'ip': self.ip,
            'recipient': self.user,
            'username': self.login_user.username,
            'name': self.login_user.name,
            'asset': str(self.asset),
            'account': self.input_username,
            'account_name': self.account.name,
            'acl_name': self.acl_name,
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
