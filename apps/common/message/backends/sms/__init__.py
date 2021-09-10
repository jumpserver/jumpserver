from collections import OrderedDict
import importlib

from django.utils.translation import gettext_lazy as _
from django.db.models import TextChoices
from django.conf import settings

from common.utils import get_logger
from common.exceptions import JMSException

logger = get_logger(__file__)


class SMS_MESSAGE(TextChoices):
    """
    定义短信的各种消息类型，会存到类似 `ALIBABA_SMS_SIGN_AND_TEMPLATES` settings 里

    {
        'verification_code': {'sign_name': 'Jumpserver', 'template_code': 'SMS_222870834'}，
        ...
    }
    """

    """
    验证码签名和模板。模板例子:
    `您的验证码：${code}，您正进行身份验证，打死不告诉别人！`
    其中必须包含 `code` 变量
    """
    VERIFICATION_CODE = 'verification_code'

    def get_sign_and_tmpl(self, config: dict):
        try:
            data = config[self]
            return data['sign_name'], data['template_code']
        except KeyError as e:
            raise JMSException(
                code=f'{settings.SMS_BACKEND}_sign_and_tmpl_bad',
                detail=_('Invalid SMS sign and template: {}').format(e)
            )


class BACKENDS(TextChoices):
    ALIBABA = 'alibaba', _('Alibaba cloud')
    TENCENT = 'tencent', _('Tencent cloud')


class BaseSMSClient:
    """
    短信终端的基类
    """

    SIGN_AND_TMPL_SETTING_FIELD: str

    @property
    def sign_and_tmpl(self):
        return getattr(settings, self.SIGN_AND_TMPL_SETTING_FIELD, {})

    @classmethod
    def new_from_settings(cls):
        raise NotImplementedError

    def send_sms(self, phone_numbers: list, sign_name: str, template_code: str, template_param: dict, **kwargs):
        raise NotImplementedError


class SMS:
    client: BaseSMSClient

    def __init__(self, backend=None):
        backend = backend or settings.SMS_BACKEND
        if backend not in BACKENDS:
            raise JMSException(
                code='sms_provider_not_support',
                detail=_('SMS provider not support: {}').format(backend)
            )
        m = importlib.import_module(f'.{backend or settings.SMS_BACKEND}', __package__)
        self.client = m.client.new_from_settings()

    def send_sms(self, phone_numbers: list, sign_name: str, template_code: str, template_param: dict, **kwargs):
        return self.client.send_sms(
            phone_numbers=phone_numbers,
            sign_name=sign_name,
            template_code=template_code,
            template_param=template_param,
            **kwargs
        )

    def send_verify_code(self, phone_number, code):
        sign_name, template_code = SMS_MESSAGE.VERIFICATION_CODE.get_sign_and_tmpl(self.client.sign_and_tmpl)
        return self.send_sms([phone_number], sign_name, template_code, OrderedDict(code=code))
