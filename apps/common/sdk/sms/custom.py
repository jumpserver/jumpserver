import requests

from collections import OrderedDict

from django.conf import settings

from common.utils import get_logger
from common.exceptions import JMSException

from .base import BaseSMSClient


logger = get_logger(__file__)


class CustomSMS(BaseSMSClient):
    @classmethod
    def new_from_settings(cls):
        return cls()

    @staticmethod
    def need_pre_check():
        return False

    def send_sms(self, phone_numbers: list, template_param: OrderedDict, **kwargs):
        phone_numbers_str = ','.join(phone_numbers)
        params = {}
        for k, v in settings.CUSTOM_SMS_API_PARAMS.items():
            params[k] = v.format(
                code=template_param.get('code'), phone_numbers=phone_numbers_str
            )

        logger.info(f'Custom sms send: phone_numbers={phone_numbers}, param={params}')
        if settings.CUSTOM_SMS_REQUEST_METHOD == 'post':
            action = requests.post
            kwargs = {'json': params}
        else:
            action = requests.get
            kwargs = {'params': params}
        try:
            response = action(url=settings.CUSTOM_SMS_URL, verify=False, **kwargs)
            if response.reason != 'OK':
                raise JMSException(detail=response.text, code=response.status_code)
        except Exception as exc:
            logger.error('Custom sms error: {}'.format(exc))


client = CustomSMS
