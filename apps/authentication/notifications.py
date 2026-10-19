from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger, get_request_ip
from common.utils.timezone import local_now_display
from common.views.template import custom_render_to_string
from jumpserver.utils import get_current_request
from notifications.backends import BACKEND
from notifications.notifications import SystemMessage, UserMessage

logger = get_logger(__file__)

CREDENTIAL_TYPE_LABELS = {
    'passkey': _('Passkey'),
    'ssh_key': _('SSH key'),
    'access_key': _('Access key'),
    'temp_token': _('Temporary password'),
    'connection_token': _('Connection token'),
    'access_token': _('Access token'),
    'private_token': _('Private token'),
}


def _display_time(value):
    if not value:
        return ''
    return timezone.localtime(value).strftime('%Y-%m-%d %H:%M:%S')


def publish_credential_created(user, credential_type, identifier='', request=None):
    if not user or user.is_service_account:
        return
    request = request or get_current_request()
    remote_addr = get_request_ip(request) if request else '-'
    transaction.on_commit(lambda: CredentialCreatedMessage(
        user, credential_type, identifier, remote_addr
    ).publish_async())


def publish_login_blocked(block_type, username, ip, count, lock_minutes):
    try:
        LoginBlockedMessage(block_type, username, ip, count, lock_minutes).publish_async()
    except Exception:
        logger.exception('Failed to publish login failure alert')


class LoginBlockedMessage(SystemMessage):
    category = 'Authentication'
    category_label = _('Authentication')
    message_type_label = _('Login failure alert')
    subject = message_type_label
    template_name = 'authentication/_msg_login_blocked.html'
    contexts = [
        {"name": "block_type", "label": _('Lockout type'), "default": "User"},
        {"name": "username", "label": _('Username'), "default": "john"},
        {"name": "ip", "label": _('IP'), "default": "192.0.2.10"},
        {"name": "count", "label": _('Login failures count'), "default": 7},
        {"name": "lock_minutes", "label": _('Lockout duration (minutes)'), "default": 30},
        {"name": "time", "label": _('Time'), "default": "2025-01-01 12:00:00"},
    ]

    def __init__(self, block_type, username, ip, count, lock_minutes):
        self.block_type = block_type
        self.username = username
        self.ip = ip
        self.count = count
        self.lock_minutes = lock_minutes
        self.time = local_now_display()

    def get_html_msg(self):
        block_types = {'user': _('User'), 'ip': _('IP'), 'mfa': _('MFA')}
        context = {
            'block_type': block_types[self.block_type],
            'username': self.username,
            'ip': self.ip,
            'count': self.count,
            'lock_minutes': self.lock_minutes,
            'time': self.time,
        }
        return {
            'subject': str(self.subject),
            'message': custom_render_to_string(self.template_name, context),
        }

    @classmethod
    def post_insert_to_db(cls, subscription):
        from rbac.models import Role, RoleBinding
        from users.models import User

        admin_role = Role.BuiltinRole.system_admin.get_role()
        admin_ids = RoleBinding.objects.filter(role=admin_role).values_list('user_id', flat=True)
        subscription.users.add(*User.objects.filter(id__in=admin_ids))
        subscription.receive_backends = [BACKEND.EMAIL]
        subscription.save()

    @classmethod
    def gen_test_msg(cls):
        return cls('user', 'john', '192.0.2.10', 7, 30)


class CredentialCreatedMessage(UserMessage):
    subject = _('Credential created reminder')
    template_name = 'authentication/_msg_credential_created.html'
    contexts = [
        {"name": "name", "label": _('Name'), "default": "John"},
        {"name": "credential_type", "label": _('Credential type'), "default": "Access key"},
        {"name": "identifier", "label": _('Identifier'), "default": "1a2b3c4d...9abc"},
        {"name": "remote_addr", "label": _('IP'), "default": "192.0.2.10"},
        {"name": "time", "label": _('Time'), "default": "2025-01-01 12:00:00"},
    ]

    def __init__(self, user, credential_type, identifier, remote_addr):
        super().__init__(user)
        self.credential_type = credential_type
        self.identifier = str(identifier) if identifier else '-'
        self.remote_addr = remote_addr or '-'
        self.time = local_now_display()

    def get_html_msg(self):
        context = {
            'name': self.user.name,
            'credential_type': str(CREDENTIAL_TYPE_LABELS[self.credential_type]),
            'identifier': self.identifier,
            'remote_addr': self.remote_addr,
            'time': self.time,
        }
        return {
            'subject': str(self.subject),
            'message': custom_render_to_string(self.template_name, context),
        }


class CredentialActivityDigestMessage(UserMessage):
    subject = _('Credential activity summary')
    template_name = 'authentication/_msg_credential_activity_digest.html'
    contexts = [
        {"name": "name", "label": _('Name'), "default": "John"},
        {"name": "items", "label": _('Credential activity'), "default": []},
    ]

    def __init__(self, user, items):
        super().__init__(user)
        self.items = items

    def get_html_msg(self):
        items = [{
            **item,
            'credential_type': str(CREDENTIAL_TYPE_LABELS[item['credential_type']]),
            'identifier': (
                f"{item['identifier'][:8]}...{item['identifier'][-4:]}"
                if len(item['identifier']) > 16 else item['identifier']
            ),
            'date_created': _display_time(item.get('date_created')),
            'date_last_used': _display_time(item.get('date_last_used')),
        } for item in self.items]
        context = {'name': self.user.name, 'items': items}
        return {
            'subject': str(self.subject),
            'message': custom_render_to_string(self.template_name, context),
        }


class DifferentCityLoginMessage(UserMessage):
    subject = _('Different city login reminder')
    template_name = 'authentication/_msg_different_city.html'
    contexts = [
        {"name": "city", "label": _('Login city'), "default": "Shanghai"},
        {"name": "username", "label": _('User'), "default": "john"},
        {"name": "name", "label": _('Name'), "default": "John"},
        {"name": "ip", "label": "IP", "default": "192.168.1.1"},
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
            'subject': str(self.subject),
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
        {"name": "username", "label": _('User'), "default": "john"},
        {"name": "name", "label": _('Name'), "default": "John"},
        {"name": "ip", "label": "IP", "default": "192.168.1.1"},
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
            'subject': str(subject),
            'message': message
        }

    @classmethod
    def gen_test_msg(cls):
        from users.models import User
        user = User.objects.first()
        ip = '8.8.8.8'
        return cls(user, ip, _('WeCom'), '000000')
