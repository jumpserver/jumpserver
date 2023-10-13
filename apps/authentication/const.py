from django.db.models import TextChoices

from authentication.confirm import CONFIRM_BACKENDS
from .confirm import ConfirmMFA, ConfirmPassword, ConfirmReLogin
from .mfa import MFAOtp, MFASms, MFARadius, MFACustom

RSA_PRIVATE_KEY = 'rsa_private_key'
RSA_PUBLIC_KEY = 'rsa_public_key'

CONFIRM_BACKEND_MAP = {backend.name: backend for backend in CONFIRM_BACKENDS}


class ConfirmType(TextChoices):
    RELOGIN = ConfirmReLogin.name, ConfirmReLogin.display_name
    PASSWORD = ConfirmPassword.name, ConfirmPassword.display_name
    MFA = ConfirmMFA.name, ConfirmMFA.display_name

    @classmethod
    def get_can_confirm_types(cls, confirm_type):
        start = cls.values.index(confirm_type)
        types = cls.values[start:]
        types.reverse()
        return types

    @classmethod
    def get_prop_backends(cls, confirm_type):
        types = cls.get_can_confirm_types(confirm_type)
        backend_classes = [
            CONFIRM_BACKEND_MAP[tp]
            for tp in types if tp in CONFIRM_BACKEND_MAP
        ]
        return backend_classes


class MFAType(TextChoices):
    OTP = MFAOtp.name, MFAOtp.display_name
    SMS = MFASms.name, MFASms.display_name
    Radius = MFARadius.name, MFARadius.display_name
    Custom = MFACustom.name, MFACustom.display_name
