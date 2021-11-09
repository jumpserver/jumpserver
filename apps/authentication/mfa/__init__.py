from .otp import MFAOtp, otp_failed_msg
from .sms import MFASms
from .radius import MFARadius

MFA_BACKENDS = [MFAOtp, MFASms, MFARadius]
