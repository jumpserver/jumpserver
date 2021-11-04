from .otp import MFAOtp
from .sms import MFASms
from .radius import MFARadius


MFA_BACKENDS = [MFAOtp, MFASms, MFARadius]


def get_enabled_mfa_backends():
    backends = [cls for cls in MFA_BACKENDS if cls.enabled()]
    backends_enabled = [backend for backend in backends if backend.enabled()]
    return backends_enabled


def get_user_set_mfa_backends(user):
    backends = get_enabled_mfa_backends()
    backends_instance = [cls(user) for cls in backends]
    backends_set = [backend.__class__ for backend in backends_instance if backend.has_set()]
    return backends_set

