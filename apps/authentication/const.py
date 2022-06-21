from django.db.models import TextChoices

from .confirm import ConfirmMFA, ConfirmPassword, ConfirmReLogin
from .mfa import MFAOtp, MFASms, MFARadius

RSA_PRIVATE_KEY = 'rsa_private_key'
RSA_PUBLIC_KEY = 'rsa_public_key'


class ConfirmType(TextChoices):
    ReLogin = ConfirmReLogin.name, ConfirmReLogin.display_name
    PASSWORD = ConfirmPassword.name, ConfirmPassword.display_name
    MFA = ConfirmMFA.name, ConfirmMFA.display_name

    @classmethod
    def next(cls, name: str):
        index = cls.values.index(name) + 1
        if index >= len(cls.values):
            return None
        return cls.values[index]

    @classmethod
    def prev(cls, name: str):
        index = cls.values.index(name) - 1
        if index < 0:
            return None
        return cls.values[index]

    @classmethod
    def compare(cls, former: str, latter: str) -> bool:
        values = cls.values
        return (values.index(former) - values.index(latter)) > 0


class MFAType(TextChoices):
    OTP = MFAOtp.name, MFAOtp.display_name
    SMS = MFASms.name, MFASms.display_name
    Radius = MFARadius.name, MFARadius.display_name
