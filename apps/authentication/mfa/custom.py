from django.conf import settings
from django.utils.module_loading import import_string
from django.utils.translation import gettext_lazy as _

from common.utils import get_logger
from .base import BaseMFA

logger = get_logger(__file__)

mfa_custom_method = None

if settings.MFA_CUSTOM:
    """ 保证自定义的方法在服务运行时不能被更改，只在第一次调用时加载一次 """
    try:
        mfa_custom_method_path = 'data.mfa.main.check_code'
        mfa_custom_method = import_string(mfa_custom_method_path)
    except Exception as e:
        logger.warning('Import custom auth method failed: {}, Maybe not enabled'.format(e))

custom_failed_msg = _("MFA Custom code invalid")


class MFACustom(BaseMFA):
    name = 'mfa_custom'
    display_name = 'Custom'
    placeholder = _("MFA custom verification code")

    def check_code(self, code):
        assert self.is_authenticated()
        ok = False
        try:
            ok = mfa_custom_method(user=self.user, code=code)
        except Exception as exc:
            logger.error('Custom authenticate error: {}'.format(exc))
        msg = '' if ok else custom_failed_msg
        return ok, msg

    def is_active(self):
        return True

    @staticmethod
    def global_enabled():
        return settings.MFA_CUSTOM and callable(mfa_custom_method)

    def get_enable_url(self) -> str:
        return ''

    def can_disable(self):
        return False

    def disable(self):
        return ''

    @staticmethod
    def help_text_of_disable():
        return _("MFA custom global enabled, cannot disable")

    def get_disable_url(self) -> str:
        return ''
