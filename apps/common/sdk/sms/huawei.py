import base64
import hashlib
import time
import uuid

import requests

from collections import OrderedDict

from django.conf import settings
from common.exceptions import JMSException
from common.utils import get_logger

from .base import BaseSMSClient

logger = get_logger(__file__)


class HuaweiClient:
    def __init__(self, app_key, app_secret, url, sign_channel_num):
        self.url = url[:-1] if url.endswith('/') else url
        self.app_key = app_key
        self.app_secret = app_secret
        self.sign_channel_num = sign_channel_num

    def build_wsse_header(self):
        now = time.strftime('%Y-%m-%dT%H:%M:%SZ')
        nonce = str(uuid.uuid4()).replace('-', '')
        digest = hashlib.sha256((nonce + now + self.app_secret).encode()).hexdigest()
        digestBase64 = base64.b64encode(digest.encode()).decode()
        formatter = 'UsernameToken Username="{}",PasswordDigest="{}",Nonce="{}",Created="{}"'
        return formatter.format(self.app_key, digestBase64, nonce, now)

    def send_sms(self, receiver, signature, template_id, template_param):
        sms_url = '%s/%s' % (self.url, 'sms/batchSendSms/v1')
        headers = {
            'Authorization': 'WSSE realm="SDP",profile="UsernameToken",type="Appkey"',
            'X-WSSE': self.build_wsse_header()
        }
        body = {
            'from': self.sign_channel_num, 'to': receiver, 'templateId': template_id,
            'templateParas': template_param, 'signature': signature
        }
        try:
            response = requests.post(sms_url, headers=headers, data=body)
            msg = response.json()
        except Exception as error:
            raise JMSException(code='response_bad', detail=error)
        return msg


class HuaweiSMS(BaseSMSClient):
    SIGN_AND_TMPL_SETTING_FIELD_PREFIX = 'HUAWEI'

    @classmethod
    def new_from_settings(cls):
        return cls(
            app_key=settings.HUAWEI_APP_KEY,
            app_secret=settings.HUAWEI_APP_SECRET,
            url=settings.HUAWEI_SMS_ENDPOINT,
            sign_channel_num=settings.HUAWEI_SIGN_CHANNEL_NUM
        )

    def __init__(self, app_key: str, app_secret: str, url: str, sign_channel_num: str):
        self.client = HuaweiClient(app_key, app_secret, url, sign_channel_num)

    def send_sms(
            self, phone_numbers: list, sign_name: str, template_code: str,
            template_param: OrderedDict, **kwargs
    ):
        phone_numbers_str = ','.join(phone_numbers)
        template_param = '["%s"]' % template_param.get('code')
        req_params = {
            'receiver': phone_numbers_str, 'signature': sign_name,
            'template_id': template_code, 'template_param': template_param
        }
        try:
            logger.info(f'Huawei sms send: '
                        f'phone_numbers={phone_numbers} '
                        f'sign_name={sign_name} '
                        f'template_code={template_code} '
                        f'template_param={template_param}')

            resp_msg = self.client.send_sms(**req_params)

        except Exception as error:
            raise JMSException(code='response_bad', detail=error)

        resp_code = resp_msg.get('code', '')
        resp_desc = resp_msg.get('description', '')
        if resp_code != '000000':
            raise JMSException(code='response_bad',
                               detail="{}:{},{}:{}".format("code", resp_code, "description", resp_desc))
        return resp_msg


client = HuaweiSMS
