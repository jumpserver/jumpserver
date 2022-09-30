from datetime import datetime

from django.db import transaction
from django.core.cache import cache

from common.utils import get_request_ip, get_logger
from common.utils.timezone import as_current_tz
from common.utils.encode import Singleton
from settings.serializers import SettingsSerializer
from jumpserver.utils import current_request
from audits.models import OperateLog


logger = get_logger(__name__)


class ModelClient:
    @staticmethod
    def save(**kwargs):
        log_id = kwargs.get('id', '')
        op_log = OperateLog.objects.filter(pk=log_id).first()
        if op_log is not None:
            raw_after = op_log.after or {}
            raw_before = op_log.before or {}
            cur_before = kwargs.get('before', {})
            cur_after = kwargs.get('after', {})
            raw_before.update(cur_before)
            raw_after.update(cur_after)
            op_log.before = raw_before
            op_log.after = raw_after
            op_log.save()
        else:
            OperateLog.objects.create(**kwargs)

    @staticmethod
    def update(log_id, **kwargs):
        OperateLog.objects.update(id=log_id, **kwargs)


class ESClient:
    @staticmethod
    def save(**kwargs):
        pass

    @staticmethod
    def update(log_id, **kwargs):
        pass


class OperatorLogHandler(metaclass=Singleton):
    CACHE_KEY = 'OPERATOR_LOG_CACHE_KEY'

    def __init__(self):
        self.log_client = self.get_storage_client()

    @staticmethod
    def get_storage_client():
        client = ModelClient()
        return client

    @staticmethod
    def _consistent_type_to_str(value1, value2):
        if isinstance(value1, datetime):
            value1 = as_current_tz(value1).strftime('%Y-%m-%d %H:%M:%S')
        if isinstance(value2, datetime):
            value2 = as_current_tz(value2).strftime('%Y-%m-%d %H:%M:%S')
        value1, value2 = str(value1), str(value2)
        return value1, value2

    def _look_for_two_dict_change(self, left_dict, right_dict):
        # 以右边的字典为基础
        before, after = {}, {}
        for key, value in right_dict.items():
            pre_value = left_dict.get(key, '')
            pre_value, value = self._consistent_type_to_str(pre_value, value)
            if value == pre_value:
                continue
            if pre_value:
                before[key] = pre_value
            if value:
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
            return None

        key = '%s_%s' % (self.CACHE_KEY, instance_id)
        cache_instance = cache.get(key, {})
        log_id = cache_instance.get('operate_log_id')
        return log_id, cache_instance

    def get_instance_current_with_cache_diff(self, current_instance):
        log_id, before, after = None, None, None
        instance_id = current_instance.get('id')
        if instance_id is None:
            return log_id, before, after

        log_id, cache_instance = self.get_instance_dict_from_cache(instance_id)
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
    def data_desensitization(before, after):
        encrypt_value = '******'
        if before:
            for key, value in before.items():
                if str(value).startswith('encrypt|'):
                    before[key] = encrypt_value
        if after:
            for key, value in after.items():
                if str(value).startswith('encrypt|'):
                    after[key] = encrypt_value
        return before, after

    def create_or_update_operate_log(
            self, action, resource_type, resource=None,
            force=False, log_id=None, before=None, after=None
    ):
        user = current_request.user if current_request else None
        if not user or not user.is_authenticated:
            return

        remote_addr = get_request_ip(current_request)
        resource_display = self.get_resource_display(resource)
        before, after = self.data_desensitization(before, after)
        if not force and not any([before, after]):
            # 前后都没变化，没必要生成日志，除非手动强制保存
            return

        data = {
            'id': log_id, "user": str(user), 'action': action,
            'resource_type': resource_type, 'resource': resource_display,
            'remote_addr': remote_addr, 'before': before, 'after': after
        }
        with transaction.atomic():
            try:
                self.log_client.save(**data)
            except Exception as e:
                error_msg = 'An error occurred saving OperateLog.' \
                            'Error: %s, Data: %s' % (e, data)
                logger.error(error_msg)


op_handler = OperatorLogHandler()
create_or_update_operate_log = op_handler.create_or_update_operate_log

cache_instance_before_data = op_handler.cache_instance_before_data
get_instance_current_with_cache_diff = op_handler.get_instance_current_with_cache_diff
get_instance_dict_from_cache = op_handler.get_instance_dict_from_cache
