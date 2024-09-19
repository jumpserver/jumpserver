from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from common.exceptions import JMSException
from common.sdk.sms.endpoint import SMS
from common.sdk.sms.exceptions import CodeError, CodeExpired, CodeSendTooFrequently
from common.tasks import send_mail_async
from common.utils import get_logger
from common.utils.random import random_string

logger = get_logger(__file__)


@shared_task(
    verbose_name=_('Send SMS code'),
    description=_(
        """When resetting a password, forgetting a password, or verifying MFA, this task needs to 
        be executed to send SMS messages"""
    )
)
def send_sms_async(target, code):
    SMS().send_verify_code(target, code)


class SendAndVerifyCodeUtil(object):
    KEY_TMPL = 'auth-verify-code-{}'

    def __init__(self, target, code=None, key=None, backend='email', timeout=None, **kwargs):
        self.code = code
        self.target = target
        self.backend = backend
        self.key = key or self.KEY_TMPL.format(target)
        self.timeout = settings.VERIFY_CODE_TTL if timeout is None else timeout
        self.other_args = kwargs

    def gen_and_send_async(self):
        ttl = self.__ttl()
        if ttl > 0:
            logger.warning('Send sms too frequently, delay {}'.format(ttl))
            raise CodeSendTooFrequently(ttl)

        return self.gen_and_send()

    def gen_and_send(self):
        try:
            if not self.code:
                self.code = self.__generate()
            self.__send(self.code)
        except JMSException:
            self.__clear()
            raise

    def verify(self, code):
        right = cache.get(self.key)
        if not right:
            raise CodeExpired

        if right != code:
            raise CodeError

        self.__clear()
        return True

    def __clear(self):
        cache.delete(self.key)

    def __ttl(self):
        return cache.ttl(self.key)

    def __get_code(self):
        return cache.get(self.key)

    def __generate(self):
        code = random_string(settings.SMS_CODE_LENGTH, lower=False, upper=False)
        self.code = code
        return code

    def __send_with_sms(self):
        send_sms_async.apply_async(args=(self.target, self.code), priority=100)

    def __send_with_email(self):
        subject = self.other_args.get('subject', '')
        message = self.other_args.get('message', '')
        send_mail_async.apply_async(
            args=(subject, message, [self.target]),
            kwargs={'html_message': message}, priority=100
        )

    def __send(self, code):
        """
        发送信息的方法，如果有错误直接抛出 api 异常
        """
        if self.backend == 'sms':
            self.__send_with_sms()
        else:
            self.__send_with_email()

        cache.set(self.key, self.code, self.timeout)
        logger.debug(f'Send verify code to {self.target}')
