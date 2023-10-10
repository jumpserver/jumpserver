import os

from collections import OrderedDict

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.utils.module_loading import import_string

from common.utils import get_logger
from common.exceptions import JMSException
from jumpserver.settings import get_file_md5

from .base import BaseSMSClient


logger = get_logger(__file__)


custom_sms_method = None
SMS_CUSTOM_FILE_MD5 = settings.SMS_CUSTOM_FILE_MD5
SMS_CUSTOM_FILE_PATH = os.path.join(settings.PROJECT_DIR, 'data', 'sms', 'main.py')
if SMS_CUSTOM_FILE_MD5 == get_file_md5(SMS_CUSTOM_FILE_PATH):
    try:
        custom_sms_method_path = 'data.sms.main.send_sms'
        custom_sms_method = import_string(custom_sms_method_path)
    except Exception as e:
        logger.warning('Import custom sms method failed: {}, Maybe not enabled'.format(e))


class CustomFileSMS(BaseSMSClient):
    @classmethod
    def new_from_settings(cls):
        return cls()

    @staticmethod
    def need_pre_check():
        return False

    def send_sms(self, phone_numbers: list, template_param: OrderedDict, **kwargs):
        if not callable(custom_sms_method):
            raise JMSException(_('The custom sms file is invalid'))

        try:
            logger.info(f'Custom file sms send: phone_numbers={phone_numbers}, param={template_param}')
            custom_sms_method(phone_numbers, template_param, **kwargs)
        except Exception as err:
            raise JMSException(_('SMS sending failed[%s]: %s') % (f"{_('Custom type')}({_('File')})", err))


client = CustomFileSMS
