# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _


class UKeyAuthError(Exception):
    """证书认证失败基类，所有子类须带可展示给用户的 msg。"""
    default_msg = _('Certificate authentication failed')

    def __init__(self, msg=None, **kwargs):
        self.msg = msg or self.default_msg
        super().__init__(str(self.msg))


class UKeyUserNotFoundError(UKeyAuthError):
    default_msg = _('User does not exist')


class UkeySNMismatchError(UKeyAuthError):
    default_msg = _('UKey SN mismatch')


class UKeyCertNormalizationError(UKeyAuthError):
    default_msg = _('Invalid certificate format')


class UKeyCertChainError(UKeyAuthError):
    default_msg = _('Certificate chain verification failed')


class UKeyCertCNMismatchError(UKeyAuthError):
    default_msg = _('Certificate CN does not match the username')


class UKeySignatureError(UKeyAuthError):
    default_msg = _('Certificate signature verification failed')


class UKeyCertExpiredError(UKeyAuthError):
    default_msg = _('Certificate has expired or is not yet valid')


class UKeyCertUnsupportedAlgorithmError(UKeyAuthError):
    default_msg = _('Unsupported certificate algorithm')
