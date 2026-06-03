# -*- coding: utf-8 -*-
#
from django.utils.translation import gettext_lazy as _


class CertAuthError(Exception):
    """证书认证失败基类，所有子类须带可展示给用户的 msg。"""
    default_msg = _('Certificate authentication failed')

    def __init__(self, msg=None, **kwargs):
        self.msg = msg or self.default_msg
        super().__init__(str(self.msg))


class CertUserNotFoundError(CertAuthError):
    default_msg = _('User does not exist')


class CertUkeySNMismatchError(CertAuthError):
    default_msg = _('UKey SN mismatch')


class CertNormalizationError(CertAuthError):
    default_msg = _('Invalid certificate format')


class CertChainError(CertAuthError):
    default_msg = _('Certificate chain verification failed')


class CertCNMismatchError(CertAuthError):
    default_msg = _('Certificate CN does not match the username')


class CertSignatureError(CertAuthError):
    default_msg = _('Certificate signature verification failed')


class CertUnsupportedAlgorithmError(CertAuthError):
    default_msg = _('Unsupported certificate algorithm')
