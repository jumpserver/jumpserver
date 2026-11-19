from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from common.exceptions import JMSException
from common.sdk.sms.endpoint import SMS
from common.sdk.sms.exceptions import CodeError, CodeExpired, CodeSendTooFrequently
from common.tasks import deliver_mail, task_activity_callback
from common.utils import get_logger
from common.utils.random import random_string

logger = get_logger(__file__)


# 验证码任务不保存执行参数，也不允许从历史记录重跑。
VERIFY_CODE_TASKS = {
    'common.utils.verify_code.send_sms_async',
    'common.utils.verify_code.send_verify_mail_async',
}


class VerifyCodeDeliveryError(Exception):
    pass


def verify_mail_activity_callback(self, subject, target, *args, **kwargs):
    # 仅按收件地址关联用户，不向活动回调传入验证码正文。
    return task_activity_callback(self, subject, None, [target])


@shared_task(
    verbose_name=_('Send SMS code'),
    # 预期异常仍标记为 FAILURE，仅省略 Celery 的异常堆栈日志。
    throws=(VerifyCodeDeliveryError,),
    description=_(
        """When resetting a password, forgetting a password, or verifying MFA, this task needs to 
        be executed to send SMS messages"""
    )
)
def send_sms_async(target, *, code, user_info=None):
    # 验证码仅接受关键字参数，避免将旧消息中的位置参数缓存键当作验证码发送。
    try:
        SMS().send_verify_code(target, code, user_info=user_info)
    except Exception as exc:
        logger.error('Verification SMS delivery failed: %s', type(exc).__name__)
        raise VerifyCodeDeliveryError('Verification SMS delivery failed') from None


@shared_task(
    verbose_name=_('Send verify code email'),
    activity_callback=verify_mail_activity_callback,
    throws=(VerifyCodeDeliveryError,),
    description=_(
        """When resetting a password, forgetting a password, or verifying MFA, this task needs to
        be executed to send verification code emails"""
    )
)
def send_verify_mail_async(subject, target, *, message):
    # 正文仅接受关键字参数，拒绝将旧消息中的位置参数缓存键当作正文发送。
    try:
        deliver_mail(subject, message, [target], html_message=message, safe_errors=True)
    except Exception as exc:
        logger.error('Verification email delivery failed: %s', type(exc).__name__)
        raise VerifyCodeDeliveryError('Verification email delivery failed') from None


class SendAndVerifyCodeUtil(object):
    KEY_TMPL = 'auth-verify-code-{}'

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
        send_sms_async.apply_async(  # type: ignore[attr-defined]
            args=(self.target,),
            kwargs={'code': self.code, 'user_info': self.user_info},
            # 隐藏 Celery 参数展示和事件中的验证码、用户信息，不改变实际发送参数。
            kwargsrepr='{}', priority=100
        )

    def __send_with_email(self):
        subject = self.other_args.get('subject', '')
        message = self.other_args.get('message', '')
        send_verify_mail_async.apply_async(  # type: ignore[attr-defined]
            args=(subject, self.target), kwargs={'message': message},
            # 隐藏 Celery 参数展示和事件中含验证码的正文，不改变实际发送参数。
            kwargsrepr='{}', priority=100
        )

    def __send(self, code):
        """
        发送信息的方法，如果有错误直接抛出 api 异常
        """
        if self.backend == 'sms':
            self.__send_with_sms()
        else:
            self.__send_with_email()
        # 发布成功后才写入校验缓存，避免发布失败后仍阻止用户重新发码。
        cache.set(self.key, code, self.timeout)
        logger.debug(f'Send verify code to {self.target}')
