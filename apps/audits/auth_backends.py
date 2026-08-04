from django.conf import settings
from django.utils import translation
from django.utils.functional import LazyObject
from django.utils.translation import gettext_lazy as _

from users.models import User


def get_auth_backend_label_mapping():
    mapping = {}
    for source, backends in User.SOURCE_BACKEND_MAPPING.items():
        for backend in backends:
            mapping[backend] = source.label
    mapping.update({
        settings.AUTH_BACKEND_PUBKEY: _('SSH Key'),
        settings.AUTH_BACKEND_MODEL: _('Password'),
        settings.AUTH_BACKEND_SSO: _('SSO'),
        settings.AUTH_BACKEND_CUSTOM_SSO: _('Custom SSO'),
        settings.AUTH_BACKEND_AUTH_TOKEN: _('Auth Token'),
        settings.AUTH_BACKEND_WECOM: _('WeCom'),
        settings.AUTH_BACKEND_FEISHU: _('FeiShu'),
        settings.AUTH_BACKEND_LARK: 'Lark',
        settings.AUTH_BACKEND_SLACK: _('Slack'),
        settings.AUTH_BACKEND_DINGTALK: _('DingTalk'),
        settings.AUTH_BACKEND_TEMP_TOKEN: _('Temporary token'),
        settings.AUTH_BACKEND_PASSKEY: _('Passkey'),
    })
    return mapping


class AuthBackendLabelMapping(LazyObject):
    def _setup(self):
        self._wrapped = get_auth_backend_label_mapping()


AUTH_BACKEND_LABEL_MAPPING = AuthBackendLabelMapping()


def get_auth_backend_choices():
    choices = []
    values = set()
    for label in get_auth_backend_label_mapping().values():
        with translation.override('en'):
            value = str(label)
        if not value or value in values:
            continue
        values.add(value)
        choices.append((value, label))
    return choices
