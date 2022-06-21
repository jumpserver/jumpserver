from .mfa import ConfirmMFA
from .password import ConfirmPassword
from .relogin import ConfirmReLogin

CONFIRM_BACKENDS = [ConfirmMFA, ConfirmPassword, ConfirmReLogin]
