from .otp import MFAOtp
from .sms import MFASms
from .radius import MFARadius


def get_supported_mfa_backends(user):
    backends_cls = [MFAOtp, MFASms, MFARadius]
    backends = [cls(user) for cls in backends_cls]
    backends_enabled = [backend for backend in backends if backend.enabled()]
    return backends_enabled

