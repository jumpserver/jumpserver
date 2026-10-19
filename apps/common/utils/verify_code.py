from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from common.exceptions import JMSException
from common.sdk.sms.endpoint import SMS
from common.sdk.sms.exceptions import CodeError, CodeExpired, CodeSendTooFrequently
from common.tasks import deliver_mail
from common.utils import get_logger
from common.utils.random import random_string

logger = get_logger(__file__)


def _read_and_drop_cache(key):
    value = cache.get(key)
    if value is None:
        return None
    cache.delete(key)
    return value


@shared_task(
    verbose_name=_('Send SMS code'),
    description=_(
        """When resetting a password, forgetting a password, or verifying MFA, this task needs to 
        be executed to send SMS messages"""
    )
)
def send_sms_async(target, cache_key, user_info=None):
    code = cache.get(cache_key)
    if not code:
        logger.error('Verify SMS code missing from cache: %s', cache_key)
        return
    SMS().send_verify_code(target, code, user_info=user_info)


@shared_task(
    verbose_name=_('Send verify code email'),
    description=_(
        """When resetting a password, forgetting a password, or verifying MFA, this task needs to
        be executed to send verification code emails"""
    )
)
def send_verify_mail_async(subject, target, msg_cache_key):
    message = _read_and_drop_cache(msg_cache_key)
    if not message:
        logger.error('Verify email body missing from cache: %s', msg_cache_key)
        return
    deliver_mail(subject, message, [target], html_message=message)


class SendAndVerifyCodeUtil(object):
    KEY_TMPL = 'auth-verify-code-{}'
    MSG_KEY_SUFFIX = ':message'

    def __init__(
            self, target, code=None, key=None, backend='email',
            user_info=None, timeout=None, **kwargs
    ):
        self.code = code
        self.target = target
        self.user_info = user_info
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

    def __message_key(self):
        return '{}{}'.format(self.key, self.MSG_KEY_SUFFIX)

    def __clear(self):
        cache.delete(self.key)
        cache.delete(self.__message_key())

    def __ttl(self):
        return cache.ttl(self.key)

    def __get_code(self):
        return cache.get(self.key)

    def __generate(self):
        code = random_string(settings.SMS_CODE_LENGTH, lower=False, upper=False)
        self.code = code
        return code

    def __send_with_sms(self):
        send_sms_async.apply_async(  # type: ignore[attr-defined]
            args=(self.target, self.key, self.user_info), priority=100
        )

    def __send_with_email(self):
        subject = self.other_args.get('subject', '')
        message = self.other_args.get('message', '')
        msg_key = self.__message_key()
        cache.set(msg_key, message, self.timeout)
        send_verify_mail_async.apply_async(  # type: ignore[attr-defined]
            args=(subject, self.target, msg_key), priority=100
        )

    def __send(self, code):
        """
        发送信息的方法，如果有错误直接抛出 api 异常
        """
        cache.set(self.key, self.code, self.timeout)
        if self.backend == 'sms':
            self.__send_with_sms()
        else:
            self.__send_with_email()
        logger.debug(f'Send verify code to {self.target}')
