from typing import Callable

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger, reverse
from common.utils import lazyproperty
from common.utils.timezone import local_now_display
from notifications.backends import BACKEND
from notifications.models import SystemMsgSubscription
from notifications.notifications import SystemMessage, UserMessage
from terminal.const import RiskLevelChoices
from terminal.models import Session, Command
from users.models import User

logger = get_logger(__name__)

__all__ = (
    'CommandAlertMessage', 'CommandExecutionAlert', 'StorageConnectivityMessage',
    'CommandWarningMessage'
)

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
    message_type_label = _('Command warning')

    def __init__(self, user, command):
        super().__init__(user)
        self.command = command

    def get_html_msg(self) -> dict:
        command = self.command

        command_input = command['input']
        user = command['user']
        asset = command['asset']
        account = command.get('_account', '')
        cmd_acl = command.get('_cmd_filter_acl')
        cmd_group = command.get('_cmd_group')
        session_id = command.get('session', '')
        risk_level = command['risk_level']
        org_id = command['org_id']
        org_name = command.get('_org_name') or org_id

        if session_id:
            session_url = reverse(
                'api-terminal:session-detail', kwargs={'pk': session_id},
                external=True, api_to_ui=True
            ) + '?oid={}'.format(org_id)
            session_url = session_url.replace('/terminal/sessions/', '/audit/sessions/sessions/')
        else:
            session_url = ''

        # Command ACL
        cmd_acl_name = cmd_group_name = ''
        if cmd_acl:
            cmd_acl_name = cmd_acl.name
        if cmd_group:
            cmd_group_name = cmd_group.name

        context = {
            'command': command_input,
            'user': user,
            'asset': asset,
            'account': account,
            'cmd_filter_acl': cmd_acl_name,
            'cmd_group': cmd_group_name,
            'session_url': session_url,
            'risk_level': RiskLevelChoices.get_label(risk_level),
            'org': org_name,
        }

        message = render_to_string('terminal/_msg_command_warning.html', context)
        return {
            'subject': self.subject,
            'message': message
        }


class CommandAlertMessage(CommandAlertMixin, SystemMessage):
    category = CATEGORY
    category_label = CATEGORY_LABEL
    message_type_label = _('Command reject')

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
        level = RiskLevelChoices.get_label(command['risk_level'])
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

        level = RiskLevelChoices.get_label(command['risk_level'])

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


class SessionSharingMessage(UserMessage):
    message_type_label = _('Session sharing')

    def __init__(self, user, instance):
        super().__init__(user)
        self.instance = instance

    def get_html_msg(self) -> dict:
        instance = self.instance
        context = {
            'asset': instance.session.asset,
            'created_by': instance.created_by,
            'account': instance.session.account,
            'url': instance.url,
            'verify_code': instance.verify_code,
            'org': instance.org_name,
        }
        message = render_to_string('terminal/_msg_session_sharing.html', context)
        return {
            'subject': self.message_type_label + ' ' + self.instance.created_by,
            'message': message
        }
