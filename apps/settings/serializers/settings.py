# coding: utf-8

from .basic import BasicSettingSerializer
from .advanced import AdvancedSettingSerializer
from .email import EmailSettingSerializer, EmailContentSettingSerializer
from .im import FeiShuSettingSerializer, WeComSettingSerializer, DingTalkSettingSerializer
from .auth import (
    LDAPSettingSerializer, OIDCSettingSerializer, KeycloakSettingSerializer,
    CASSettingSerializer, RadiusSettingSerializer
)
from .terminal import TerminalSettingSerializer
from .security import SecuritySettingSerializer

__all__ = [
    'SettingsSerializer',
]


class SettingsSerializer(
    BasicSettingSerializer,
    LDAPSettingSerializer,
    TerminalSettingSerializer,
    SecuritySettingSerializer,
    WeComSettingSerializer,
    DingTalkSettingSerializer,
    FeiShuSettingSerializer,
    EmailSettingSerializer,
    EmailContentSettingSerializer,
    AdvancedSettingSerializer,
    OIDCSettingSerializer,
    KeycloakSettingSerializer,
    CASSettingSerializer,
    RadiusSettingSerializer
):
    # encrypt_fields 现在使用 write_only 来判断了
    pass
