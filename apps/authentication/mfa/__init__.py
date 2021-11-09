from .otp import MFAOtp
from .sms import MFASms
from .radius import MFARadius


MFA_BACKENDS = [MFAOtp, MFASms, MFARadius]
