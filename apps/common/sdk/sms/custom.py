from collections import OrderedDict

import requests
from django.conf import settings

from common.exceptions import JMSException
from common.utils import get_logger
from .base import BaseSMSClient

logger = get_logger(__file__)


class CustomSMS(BaseSMSClient):
    def __init__(self, url=None, method=None, api_params=None, timeout=None):
        self.url = settings.CUSTOM_SMS_URL if url is None else url
        self.method = settings.CUSTOM_SMS_REQUEST_METHOD if method is None else method
        self.api_params = settings.CUSTOM_SMS_API_PARAMS if api_params is None else api_params
        self.timeout = timeout

    @classmethod
    def new_from_settings(cls):
        return cls()

    @staticmethod
    def need_pre_check():
        return False

    def send_sms(self, phone_numbers: list, template_param: OrderedDict, **kwargs):
        phone_numbers_str = ','.join(phone_numbers)
        params = {}
        for k, v in self.api_params.items():
            params[k] = v.format(
                code=template_param.get('code'), phone_numbers=phone_numbers_str
            )

        logger.info(f'Custom sms send: phone_numbers={phone_numbers}, param={params}')
        if self.method == 'post':
            action = requests.post
            kwargs = {'json': params}
        else:
            action = requests.get
            kwargs = {'params': params}
        try:
            response = action(url=self.url, verify=settings.VERIFY_EXTERNAL_SSL, timeout=self.timeout, **kwargs)
            response.raise_for_status()
        except Exception as exc:
            logger.error('Custom sms error: {}'.format(exc))
            raise JMSException(exc)


client = CustomSMS
