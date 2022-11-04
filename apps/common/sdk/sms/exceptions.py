from django.utils.translation import gettext_lazy as _

from common.exceptions import JMSException


class CodeExpired(JMSException):
    default_code = 'verify_code_expired'
    default_detail = _('The verification code has expired. Please resend it')


class CodeError(JMSException):
    default_code = 'verify_code_error'
    default_detail = _('The verification code is incorrect')


class CodeSendTooFrequently(JMSException):
    default_code = 'code_send_too_frequently'
    default_detail = _('Please wait {} seconds before sending')

    def __init__(self, ttl):
        super().__init__(detail=self.default_detail.format(ttl))
