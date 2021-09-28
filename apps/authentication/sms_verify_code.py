import random

from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from common.message.backends.sms.alibaba import AlibabaSMS
from common.message.backends.sms import SMS
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


class VerifyCodeUtil:
    KEY_TMPL = 'auth-verify_code-{}'
    TIMEOUT = 60

    def __init__(self, account, key_suffix=None, timeout=None):
        self.account = account
        self.key_suffix = key_suffix
        self.code = ''

        if key_suffix is not None:
            self.key = self.KEY_TMPL.format(key_suffix)
        else:
            self.key = self.KEY_TMPL.format(account)
        self.timeout = self.TIMEOUT if timeout is None else timeout

    def touch(self):
        """
        生成，保存，发送
        """
        ttl = self.ttl()
        if ttl > 0:
            raise CodeSendTooFrequently(ttl)
        try:
            self.generate()
            self.save()
            self.send()
        except JMSException:
            self.clear()
            raise

    def generate(self):
        code = ''.join(random.sample('0123456789', 4))
        self.code = code
        return code

    def clear(self):
        cache.delete(self.key)

    def save(self):
        cache.set(self.key, self.code, self.timeout)

    def send(self):
        """
        发送信息的方法，如果有错误直接抛出 api 异常
        """
        account = self.account
        code = self.code

        sms = SMS()
        sms.send_verify_code(account, code)
        logger.info(f'Send sms verify code: account={account} code={code}')

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
