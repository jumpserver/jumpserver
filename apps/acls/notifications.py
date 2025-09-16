from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from accounts.models import Account
from acls.models import LoginACL, LoginAssetACL
from assets.models import Asset
from audits.models import UserLoginLog
from common.views.template import custom_render_to_string
from notifications.notifications import UserMessage
from users.models import User


class UserLoginReminderMsg(UserMessage):
    subject = _('User login reminder')
    template_name = 'acls/user_login_reminder.html'
    contexts = [
        {"name": "city", "label": _('Login city'), "default": "北京"},
        {"name": "username", "label": _('User'), "default": "zhangsan"},
        {"name": "ip", "label": "IP", "default": "8.8.8.8"},
        {"name": "recipient_name", "label": _("Recipient name"), "default": "zhangsan"},
        {"name": "recipient_username", "label": _("Recipient username"), "default": "张三"},
        {"name": "user_agent", "label": _('User agent'), "default": "Mozilla/5.0"},
        {"name": "acl_name", "label": _('ACL name'), "default": "login acl"},
        {"name": "login_from", "label": _('Login from'), "default": "web"},
        {"name": "time", "label": _('Login time'), "default": "2025-01-01 12:00:00"},
    ]

    def __init__(self, user, user_log: UserLoginLog, acl: LoginACL):
        self.user_log = user_log
        self.acl_name = str(acl)
        self.login_from = user_log.get_type_display()
        now = timezone.localtime(user_log.datetime)
        self.time = now.strftime('%Y-%m-%d %H:%M:%S')
        super().__init__(user)

    def get_html_msg(self) -> dict:
        user_log = self.user_log
        context = {
            'ip': user_log.ip,
            'time': self.time,
            'city': user_log.city,
            'acl_name': self.acl_name,
            'login_from': self.login_from,
            'username': user_log.username,
            'recipient_name': self.user.name,
            'recipient_username': self.user.username,
            'user_agent': user_log.user_agent,
        }
        message = custom_render_to_string(self.template_name, context)

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
    template_name = 'acls/asset_login_reminder.html'
    contexts = [
        {"name": "city", "label": _('Login city'), "default": "北京"},
        {"name": "username", "label": _('User'), "default": "zhangsan"},
        {"name": "name", "label": _('Name'), "default": "zhangsan"},
        {"name": "asset", "label": _('Asset'), "default": "dev server"},
        {"name": "recipient_name", "label": _('Recipient name'), "default": "zhangsan"},
        {"name": "recipient_username", "label": _('Recipient username'), "default": "张三"},
        {"name": "account", "label": _('Account Input username'), "default": "root"},
        {"name": "account_name", "label": _('Account name'), "default": "root"},
        {"name": "acl_name", "label": _('ACL name'), "default": "login acl"},
        {"name": "ip", "label": "IP", "default": "192.168.1.1"},
        {"name": "login_from", "label": _('Login from'), "default": "web"},
        {"name": "time", "label": _('Login time'), "default": "2025-01-01 12:00:00"}
    ]

    def __init__(
            self, user, asset: Asset, login_user: User,
            account: Account, acl: LoginAssetACL,
            ip, input_username, login_from
    ):
        self.ip = ip
        self.asset = asset
        self.login_user = login_user
        self.account = account
        self.acl_name = str(acl)
        self.login_from = login_from
        self.login_user = login_user
        self.input_username = input_username

        now = timezone.localtime(timezone.now())
        self.time = now.strftime('%Y-%m-%d %H:%M:%S')
        super().__init__(user)

    def get_html_msg(self) -> dict:
        context = {
            'ip': self.ip,
            'time': self.time,
            'login_from': self.login_from,
            'recipient': self.user,
            'username': self.login_user.username,
            'name': self.login_user.name,
            'asset': str(self.asset),
            'account': self.input_username,
            'account_name': self.account.name,
            'acl_name': self.acl_name,
        }
        message = custom_render_to_string(self.template_name, context)

        return {
            'subject': str(self.subject),
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        user = User.objects.first()
        asset = Asset.objects.first()
        return cls(user, asset, user)
