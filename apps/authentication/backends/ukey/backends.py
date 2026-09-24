# -*- coding: utf-8 -*-
#
from django.conf import settings
from django.core.exceptions import PermissionDenied

from users.models import User, UKeyCertificateBinding
from common.utils import get_logger
from ..base import JMSBaseAuthBackend
from . import challenges
from .binding import verify_identity
from .configuration import REVISION, ensure_enabled, get_snapshot, locked_snapshot
from .exceptions import UKeyAuthError, UKeyUserNotFoundError, UkeySNMismatchError
from .providers import get_provider
from authentication.errors.const import reason_user_inactive, reason_choices


__all__ = ['UKeyBackend']

logger = get_logger(__name__)


class UKeyBackend(JMSBaseAuthBackend):
    backend = settings.AUTH_BACKEND_UKEY

    @staticmethod
    def is_enabled():
        return get_snapshot()['AUTH_UKEY']

    def authenticate(self, request, username, ukey_proof=None):
        if ukey_proof is None:
            return None
        try:
            cert = ukey_proof.get('cert')
            signature = ukey_proof.get('signature')
            ukey_sn = ukey_proof.get('ukey_sn')
            provider = get_provider(get_snapshot())
            if provider.binding_mode == 'user_sn':
                if 'challenge' not in ukey_proof:
                    raise UKeyAuthError('UKey configuration changed; refresh and retry')
                # The builtin view reads this challenge from the session cache.
                user = self._check_user_and_ukey_sn(username, ukey_sn)
                provider.verify_proof(cert, signature, ukey_proof['challenge'], username)
                if self.user_can_authenticate(user):
                    return user
                raise PermissionDenied(reason_choices[reason_user_inactive])
            if provider.binding_mode != 'certificate':
                raise UKeyAuthError('Unsupported certificate binding mode')
            if request is None:
                raise UKeyAuthError('A UKey login session is required')
            record, snapshot = challenges.consume(request, ukey_proof.get('challenge_id'), 'login')
            provider = ensure_enabled(snapshot, record['provider'])
            challenge = record['code']
            request.ukey_auth_state = {
                'revision': snapshot[REVISION], 'provider': provider.id,
                'expires': record['expires'],
            }
            return self._authenticate_certificate(request, snapshot, cert, signature, challenge, ukey_sn)
        except Exception as e:
            if request:
                request.error_message = str(e)
            raise PermissionDenied(str(e))

    def _authenticate_certificate(self, request, snapshot, cert, signature, challenge, hardware_serial):
        identity = verify_identity(snapshot, challenge, cert, signature)
        # Match the full verified certificate; never fall back to serial/CN.
        binding = UKeyCertificateBinding.objects.select_related('user').filter(
            provider=identity['provider'], certificate_fingerprint=identity['certificate_fingerprint'],
        ).first()
        if not binding or not hardware_serial or binding.hardware_serial != hardware_serial:
            raise UKeyAuthError('Certificate or UKey is not bound to a user')
        user = binding.user
        if not self.user_can_authenticate(user) or not self.user_allow_authenticate(user):
            raise UKeyAuthError('User is not allowed to authenticate with UKey')
        with locked_snapshot(snapshot[REVISION]) as current:
            ensure_enabled(current, identity['provider'])
        request.ukey_binding_version = str(binding.version)
        return user

    def _check_user_and_ukey_sn(self, username, ukey_sn):
        """查找用户并校验 ukey_sn 绑定关系，返回 User 实例。"""
        ukey_sn = (ukey_sn or '').strip()
        user = User.objects.filter(username=username).first()
        if user is None:
            logger.error('UKeyBackend: user %r not found', username)
            raise UKeyUserNotFoundError()
        user_ukey_sn = (user.ukey_sn or '').strip()
        if not user_ukey_sn or not ukey_sn or ukey_sn != user_ukey_sn:
            logger.error('UKeyBackend: ukey_sn mismatch for user %r', username)
            raise UkeySNMismatchError()
        return user
