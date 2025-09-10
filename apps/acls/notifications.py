from django.template.loader import render_to_string
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
        {"name": "recipient_name", "label": '接收人名称', "default": "zhangsan"},
        {"name": "recipient_username", "label": '接收人用户名', "default": "张三"},
        {"name": "user_agent", "label": _('User agent'), "default": "Mozilla/5.0"},
        {"name": "acl_name", "label": _('ACL name'), "default": "login acl"},
    ]

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
            'acl_name': self.acl_name,
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
        {"name": "recipient_name", "label": '接收人名称', "default": "zhangsan"},
        {"name": "recipient_username", "label": '接收人用户名', "default": "张三"},
        {"name": "account", "label": _('Account Input username'), "default": "root"},
        {"name": "account_name", "label": _('Account name'), "default": "root"},
        {"name": "acl_name", "label": _('ACL name'), "default": "login acl"},
    ]

    def __init__(
            self, user, asset: Asset, login_user: User,
            account: Account, acl: LoginAssetACL,
            ip, input_username
    ):
        self.ip = ip
        self.asset = asset
        self.login_user = login_user
        self.account = account
        self.acl_name = str(acl)
        self.login_user = login_user
        self.input_username = input_username
        super().__init__(user)

    def get_html_msg(self) -> dict:
        context = {
            'ip': self.ip,
            'recipient_name': self.user.name,
            'recipient_username': self.user.username,
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
