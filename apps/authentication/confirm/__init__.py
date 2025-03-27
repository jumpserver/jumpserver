from .mfa import ConfirmMFA
from .password import ConfirmPassword
from .relogin import ConfirmReLogin

CONFIRM_BACKENDS = [ConfirmReLogin, ConfirmPassword, ConfirmMFA]
CONFIRM_BACKEND_MAP = {backend.name: backend for backend in CONFIRM_BACKENDS}
