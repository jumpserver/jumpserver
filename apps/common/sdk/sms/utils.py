import random

from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from .endpoint import SMS
from common.utils import get_logger
from common.exceptions import JMSException

logger = get_logger(__file__)


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


class SendAndVerifySMSUtil:
    KEY_TMPL = 'auth-verify-code-{}'
    TIMEOUT = 60

    def __init__(self, phone, key_suffix=None, timeout=None):
        self.phone = phone
        self.code = ''
        self.timeout = timeout or self.TIMEOUT
        self.key_suffix = key_suffix or str(phone)
        self.key = self.KEY_TMPL.format(self.key_suffix)

    def gen_and_send(self):
        """
        生成，保存，发送
        """
        ttl = self.ttl()
        if ttl > 0:
            logger.error('Send sms too frequently, delay {}'.format(ttl))
            raise CodeSendTooFrequently(ttl)

        try:
            code = self.generate()
            self.send(code)
        except JMSException:
            self.clear()
            raise

    def generate(self):
        code = ''.join(random.sample('0123456789', 4))
        self.code = code
        return code

    def clear(self):
        cache.delete(self.key)

    def send(self, code):
        """
        发送信息的方法，如果有错误直接抛出 api 异常
        """
        sms = SMS()
        sms.send_verify_code(self.phone, code)
        cache.set(self.key, self.code, self.timeout)
        logger.info(f'Send sms verify code to {self.phone}: {code}')

    def verify(self, code):
        right = cache.get(self.key)
        if not right:
            raise CodeExpired

        if right != code:
            raise CodeError

        self.clear()
        return True

    def ttl(self):
        return cache.ttl(self.key)

    def get_code(self):
        return cache.get(self.key)
