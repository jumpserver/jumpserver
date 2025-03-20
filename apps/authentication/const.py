from django.db.models import TextChoices
from django.utils.translation import gettext_lazy as _

RSA_PRIVATE_KEY = 'rsa_private_key'
RSA_PUBLIC_KEY = 'rsa_public_key'


class ConfirmType(TextChoices):
    RELOGIN = 'relogin', 'Re-Login'
    PASSWORD = 'password', _('Password')
    MFA = 'mfa', 'MFA'

    @classmethod
    def get_can_confirm_types(cls, confirm_type):
        start = cls.values.index(confirm_type)
        types = cls.values[start:]
        types.reverse()
        return types

    @classmethod
    def get_prop_backends(cls, confirm_type):
        from authentication.confirm import CONFIRM_BACKEND_MAP
        types = cls.get_can_confirm_types(confirm_type)
        backend_classes = [
            CONFIRM_BACKEND_MAP[tp]
            for tp in types if tp in CONFIRM_BACKEND_MAP
        ]
        return backend_classes


class MFAType(TextChoices):
    OTP = 'otp', _('OTP')
    SMS = 'sms', _('SMS')
    Face = 'face', _('Face Recognition')
    Radius = 'otp_radius', _('Radius')
    Custom = 'mfa_custom', _('Custom')


FACE_CONTEXT_CACHE_KEY_PREFIX = "FACE_CONTEXT"
FACE_CONTEXT_CACHE_TTL = 60
FACE_SESSION_KEY = "face_token"


class FaceMonitorActionChoices(TextChoices):
    Verify = 'verify', 'verify'
    Pause = 'pause', 'pause'
    Resume = 'resume', 'resume'


class ConnectionTokenType(TextChoices):
    ADMIN = 'admin', 'Admin'
    SUPER = 'super', 'Super'
    USER = 'user', 'User'
