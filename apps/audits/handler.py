import json
from datetime import datetime

from django.core.cache import cache
from django.db import transaction
from django.utils.translation import gettext_lazy as _

from common.local import encrypted_field_set
from common.utils import get_request_ip, get_logger
from common.utils.encode import Singleton
from common.utils.timezone import as_current_tz
from jumpserver.utils import current_request
from orgs.models import Organization
from orgs.utils import get_current_org_id
from settings.serializers import SettingsSerializer
from .backends import get_operate_log_storage

logger = get_logger(__name__)


class OperatorLogHandler(metaclass=Singleton):
    CACHE_KEY = 'OPERATOR_LOG_CACHE_KEY'

    def __init__(self):
        self.log_client = self.get_storage_client()

    @staticmethod
    def get_storage_client():
        client = get_operate_log_storage()
        return client

    @staticmethod
    def _consistent_type_to_str(value1, value2):
        if isinstance(value1, datetime):
            value1 = as_current_tz(value1).strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(value2, datetime):
            value2 = as_current_tz(value2).strftime('%Y-%m-%d %H:%M:%S')
        return value1, value2

    def _look_for_two_dict_change(self, left_dict, right_dict):
        # 以右边的字典为基础
        before, after = {}, {}
        for key, value in right_dict.items():
            pre_value = left_dict.get(key, '')
            pre_value, value = self._consistent_type_to_str(pre_value, value)
            if sorted(str(value)) == sorted(str(pre_value)):
                continue
            before[key] = pre_value
            after[key] = value
        return before, after

    def cache_instance_before_data(self, instance_dict):
        instance_id = instance_dict.get('id')
        if instance_id is None:
            return

        key = '%s_%s' % (self.CACHE_KEY, instance_id)
        cache.set(key, instance_dict, 3 * 60)

    def get_instance_dict_from_cache(self, instance_id):
        if instance_id is None:
            return None, None

        key = '%s_%s' % (self.CACHE_KEY, instance_id)
        cache_instance = cache.get(key, {})
        log_id = cache_instance.get('operate_log_id')
        return log_id, cache_instance

    def get_instance_current_with_cache_diff(self, current_instance):
        log_id, before, after = None, None, None
        instance_id = current_instance.get('id')
        if instance_id is None:
            return log_id, before, after

        try:
            log_id, cache_instance = self.get_instance_dict_from_cache(instance_id)
        except Exception as err:
            logger.error('Get instance diff from cache error: %s' % err)
            return log_id, before, after

        if not cache_instance:
            return log_id, before, after

        before, after = self._look_for_two_dict_change(
            cache_instance, current_instance
        )
        return log_id, before, after

    @staticmethod
    def get_resource_display_from_setting(resource):
        resource_display = None
        setting_serializer = SettingsSerializer()
        label = setting_serializer.get_field_label(resource)
        if label is not None:
            resource_display = label
        return resource_display

    def get_resource_display(self, resource):
        resource_display = str(resource)
        return_value = self.get_resource_display_from_setting(resource_display)
        if return_value is not None:
            resource_display = return_value
        return resource_display

    @staticmethod
    def serialized_value(value: (list, tuple)):
        if len(value) == 0:
            return ''
        if isinstance(value[0], str):
            return ','.join(value)
        return json.dumps(value)

    def __data_processing(self, dict_item, loop=True):
        encrypt_value = '******'
        for key, value in dict_item.items():
            if isinstance(value, bool):
                value = _('Yes') if value else _('No')
            elif isinstance(value, (list, tuple)):
                value = self.serialized_value(value)
            elif isinstance(value, dict) and loop:
                self.__data_processing(value, loop=False)
            if key in encrypted_field_set:
                value = encrypt_value
            dict_item[key] = value
        return dict_item

    def data_processing(self, before, after):
        if before:
            before = self.__data_processing(before)
        if after:
            after = self.__data_processing(after)
        return before, after

    @staticmethod
    def get_org_id(object_name):
        system_obj = ('Role',)
        org_id = get_current_org_id()
        if object_name in system_obj:
            org_id = Organization.SYSTEM_ID
        return org_id

    def create_or_update_operate_log(
            self, action, resource_type, resource=None, resource_display=None,
            force=False, log_id=None, before=None, after=None,
            object_name=None
    ):
        user = current_request.user if current_request else None
        if not user or not user.is_authenticated:
            return

        remote_addr = get_request_ip(current_request)
        if resource_display is None:
            resource_display = self.get_resource_display(resource)
        resource_id = getattr(resource, 'pk', '')
        before, after = self.data_processing(before, after)
        if not force and not any([before, after]):
            # 前后都没变化，没必要生成日志，除非手动强制保存
            return

        org_id = self.get_org_id(object_name)
        data = {
            'id': log_id, "user": str(user), 'action': action,
            'resource_type': str(resource_type), 'org_id': org_id,
            'resource_id': resource_id, 'resource': resource_display,
            'remote_addr': remote_addr, 'before': before, 'after': after,
        }
        with transaction.atomic():
            if self.log_client.ping(timeout=1):
                client = self.log_client
            else:
                logger.info('Switch default operate log storage save.')
                client = get_operate_log_storage(default=True)

            try:
                client.save(**data)
            except Exception as e:
                error_msg = 'An error occurred saving OperateLog.' \
                            'Error: %s, Data: %s' % (e, data)
                logger.error(error_msg)


op_handler = OperatorLogHandler()
# 理论上操作日志的唯一入口
create_or_update_operate_log = op_handler.create_or_update_operate_log
cache_instance_before_data = op_handler.cache_instance_before_data
get_instance_current_with_cache_diff = op_handler.get_instance_current_with_cache_diff
get_instance_dict_from_cache = op_handler.get_instance_dict_from_cache
