from typing import Callable

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

from common.utils import get_logger, reverse
from common.utils import lazyproperty
from common.utils.timezone import local_now_display
from notifications.backends import BACKEND
from notifications.models import SystemMsgSubscription
from notifications.notifications import SystemMessage, UserMessage
from terminal.models import Session, Command
from acls.models import CommandFilterACL, CommandGroup
from users.models import User

logger = get_logger(__name__)

__all__ = ('CommandAlertMessage', 'CommandExecutionAlert', 'StorageConnectivityMessage')

CATEGORY = 'terminal'
CATEGORY_LABEL = _('Sessions')


class CommandAlertMixin:
    command: dict
    _get_message: Callable
    message_type_label: str

    def __str__(self):
        return str(self.message_type_label)

    @lazyproperty
    def subject(self):
        _input = self.command['input']
        if isinstance(_input, str):
            _input = _input.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

        subject = self.message_type_label + ": %(cmd)s" % {
            'cmd': _input
        }
        return subject

    @classmethod
    def post_insert_to_db(cls, subscription: SystemMsgSubscription):
        """
        兼容操作，试图用 `settings.SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER` 的邮件地址
        assets_systemuser_assets找到用户，把用户设置为默认接收者
        """
        from settings.models import Setting
        db_setting = Setting.objects.filter(
            name='SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER'
        ).first()
        if db_setting:
            emails = db_setting.value
        else:
            emails = settings.SECURITY_INSECURE_COMMAND_EMAIL_RECEIVER
        emails = emails.split(',')
        emails = [email.strip().strip('"') for email in emails]

        users = User.objects.filter(email__in=emails)
        if users:
            subscription.users.add(*users)
            subscription.receive_backends = [BACKEND.EMAIL]
            subscription.save()


class CommandWarningMessage(CommandAlertMixin, UserMessage):
    message_type_label = _('Danger command warning')

    def __init__(self, user, command):
        super().__init__(user)
        self.command = command

    def get_html_msg(self) -> dict:
        org_id = self.command.get('org_id')
        context = {
            'command': self.command.get('input'),
        }
        session = self.command.get('_session')
        if isinstance(session, Session):
            org_id = session.org_id
            user_id = session.user_id
            context['user'] = session.user
            context['user_url'] = reverse(
                'users:user-detail', kwargs={'pk': user_id},
                api_to_ui=True, external=True, is_console=True
            ) + '?oid={}'.format(org_id),
            asset_id = session.asset_id
            context['asset'] = session.asset
            account_id = session.account_id
            context['account'] = session.account
            session_id = session.id
            context['session_id'] = session_id
            context['org'] = session.org.name
        else:
            user_id = self.command.get('user')
            context['user'] = user_id
            context['user_url'] = ''
            asset_id = self.command.get('asset')
            context['asset'] = asset_id
            account_id = self.command.get('account')
            context['account'] = account_id
            session_id = self.command.get('session')
            context['session_id'] = session_id
            context['org'] = org_id

        context['asset_url'] = reverse(
            'assets:asset-detail', kwargs={'pk': asset_id},
            api_to_ui=True, external=True, is_console=True
        ) + '?oid={}'.format(org_id),
        context['account_url'] = reverse(
            'accounts:account-detail', kwargs={'pk': account_id},
            api_to_ui=True, external=True, is_console=True
        ) + '?oid={}'.format(org_id),
        context['session_url'] = reverse(
            'api-terminal:session-detail', kwargs={'pk': session_id},
            external=True, api_to_ui=True
        ) + '?oid={}'.format(org_id) \
            .replace('/terminal/sessions/', '/audit/sessions/sessions/'),

        acl = self.command.get('_cmd_filter_acl')
        if isinstance(acl, CommandFilterACL):
            context['cmd_filter_acl'] = acl.name
            cmd_filter_acl_id = acl.id
        else:
            cmd_filter_acl_id = self.command.get('cmd_filter_acl')
            context['cmd_filter_acl'] = cmd_filter_acl_id
        context['cmd_filter_acl_url'] = settings.SITE_URL + f'/ui/#/console/perms/cmd-acls/{cmd_filter_acl_id}/'

        cmd_group = self.command.get('_cmd_group')
        if isinstance(cmd_group, CommandGroup):
            context['cmd_group'] = cmd_group.name
            cmd_group_id = cmd_group.id
        else:
            cmd_group_id = self.command.get('cmd_group')
            context['cmd_group'] = cmd_group_id
        context['cmd_group_url'] = settings.SITE_URL + f'/ui/#/console/perms/cmd-groups/{cmd_group_id}/'

        message = render_to_string('terminal/_msg_command_warning.html', context)
        return {
            'subject': self.subject,
            'message': message
        }


class CommandAlertMessage(CommandAlertMixin, SystemMessage):
    category = CATEGORY
    category_label = CATEGORY_LABEL
    message_type_label = _('Danger command alert')

    def __init__(self, command):
        self.command = command

    @classmethod
    def gen_test_msg(cls):
        command = Command.objects.first()
        if not command:
            command = Command(user='test', asset='test', input='test', session='111111111')
        else:
            command['session'] = Session.objects.first().id
        return cls(command)

    def get_html_msg(self) -> dict:
        command = self.command
        session_detail_url = reverse(
            'api-terminal:session-detail', kwargs={'pk': command['session']},
            external=True, api_to_ui=True
        ) + '?oid={}'.format(self.command['org_id'])
        session_detail_url = session_detail_url.replace(
            '/terminal/sessions/', '/audit/sessions/sessions/'
        )
        level = Command.get_risk_level_str(command['risk_level'])
        items = {
            _("Asset"): command['asset'],
            _("User"): command['user'],
            _("Level"): level,
            _("Date"): local_now_display(),
        }
        context = {
            'items': items,
            'session_url': session_detail_url,
            "command": command['input'],
        }
        message = render_to_string('terminal/_msg_command_alert.html', context)
        return {
            'subject': self.subject,
            'message': message
        }


class CommandExecutionAlert(CommandAlertMixin, SystemMessage):
    category = CATEGORY
    category_label = CATEGORY_LABEL
    message_type_label = _('Batch danger command alert')

    def __init__(self, command):
        self.command = command

    @classmethod
    def gen_test_msg(cls):
        from assets.models import Asset
        from users.models import User
        cmd = {
            'input': 'ifconfig eth0',
            'assets': Asset.objects.all()[:10],
            'user': str(User.objects.first()),
            'risk_level': 5,
        }
        return cls(cmd)

    def get_html_msg(self) -> dict:
        command = self.command
        assets_with_url = []
        for asset in command['assets']:
            url = reverse(
                'assets:asset-detail', kwargs={'pk': asset.id},
                api_to_ui=True, external=True, is_console=True
            ) + '?oid={}'.format(asset.org_id)
            assets_with_url.append([asset, url])

        level = Command.get_risk_level_str(command['risk_level'])
        items = {
            _("User"): command['user'],
            _("Level"): level,
            _("Date"): local_now_display(),
        }

        context = {
            'items': items,
            'assets_with_url': assets_with_url,
            'command': command['input'],
        }
        message = render_to_string('terminal/_msg_command_execute_alert.html', context)
        return {
            'subject': self.subject,
            'message': message
        }


class StorageConnectivityMessage(SystemMessage):
    category = 'storage'
    category_label = _('Command and replay storage')
    message_type_label = _('Connectivity alarm')

    def __init__(self, errors):
        self.errors = errors

    @classmethod
    def post_insert_to_db(cls, subscription: SystemMsgSubscription):
        subscription.receive_backends = [b for b in BACKEND if b.is_enable]
        subscription.save()

    @classmethod
    def gen_test_msg(cls):
        from terminal.models import ReplayStorage
        replay = ReplayStorage.objects.first()
        errors = [{
            'msg': str(_("Test failure: Account invalid")),
            'type': replay.get_type_display(),
            'name': replay.name
        }]
        return cls(errors)

    def get_html_msg(self) -> dict:
        context = {
            'items': self.errors,
        }
        subject = str(_("Invalid storage"))
        message = render_to_string(
            'terminal/_msg_check_command_replay_storage_connectivity.html', context
        )
        return {
            'subject': subject,
            'message': message
        }
