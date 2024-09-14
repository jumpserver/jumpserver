# -*- coding: utf-8 -*-
#
import json
import uuid

from typing import Any

from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save

from audits.const import LogStorageType
from audits.models import (
    OperateLog, UserLoginLog, PasswordChangeLog, FTPLog
)
from common.db.encoder import ModelJSONFieldEncoder
from common.utils import get_logger, data_to_json
from common.utils.timezone import local_now_display
from common.plugins.es import ES, QuerySet as ESQuerySet
from .mixin import OperateStorageMixin


logger = get_logger(__file__)


class BaseLogStorage(ES):
    model: Any  # Log model
    type = LogStorageType.es
    date_field_name = 'datetime'
    _manager = None

    def make_data(self, data):
        if not data.get('id'):
            data['id'] = str(uuid.uuid4())
        if not data.get(self.date_field_name):
            data[self.date_field_name] = local_now_display()
        return json.loads(data_to_json(data, cls=ModelJSONFieldEncoder))

    def update(self, instance, validated_data):
        other_params = {}
        es_id = getattr(instance, 'es_id', '')
        if self.version == 7:
            other_params = {'doc_type': self.doc_type}

        data = {'doc': json.loads(data_to_json(validated_data, cls=ModelJSONFieldEncoder))}
        self.es.update(
            index=self.index, id=es_id, body=data, refresh=True, **other_params
        )
        for k, v in validated_data.items():
            setattr(instance, k, v)
        return instance

    def save(self, **kwargs):
        super().save(**kwargs)
        instance = self.model.from_dict(kwargs)
        post_save.send(sender=self.model, instance=instance, created=True)
        return instance

    def get_manager(self):
        if self._manager is None:
            self._manager = ESQuerySet(self)
            self._manager.model = self.model
        return self._manager


class OperateLogStore(OperateStorageMixin, BaseLogStorage):
    model = OperateLog

    def __init__(self, config):
        properties = {
            'id': {'type': 'keyword'},
            'user': {'type': 'keyword'},
            'action': {'type': 'keyword'},
            'resource': {'type': 'keyword'},
            'resource_type': {'type': 'keyword'},
            'remote_addr': {'type': 'keyword'},
            'org_id': {'type': 'keyword'},
            'datetime': {'type': 'date', 'format': 'yyyy-MM-dd HH:mm:ss'}
        }
        keyword_fields = {k for k, v in properties.items() if v.get('type') == 'keyword'}
        exact_fields = keyword_fields | {'datetime'}
        if not config.get('INDEX', None):
            config['INDEX'] = 'jumpserver_operate_log'
        else:
            config['INDEX'] = f"{config['INDEX']}_operate_log"
        super().__init__(config, properties, keyword_fields, exact_fields=exact_fields)

    @classmethod
    def convert_diff_friendly(cls, op_log):
        diff_list = []
        handler = cls._get_special_handler(op_log.get('resource_type'))
        before = op_log.get('before') or {}
        after = op_log.get('after') or {}
        keys = set(before.keys()) | set(after.keys())
        for key in keys:
            before_v, after_v = before.get(key), after.get(key)
            diff_list.append({
                'field': _(key),
                'before': handler(key, before_v) if before_v else _('empty'),
                'after': handler(key, after_v) if after_v else _('empty'),
            })
        return diff_list

    def save(self, **kwargs):
        log_id = kwargs.get('id', '')
        before = kwargs.get('before') or {}
        after = kwargs.get('after') or {}

        op_log = None
        if log_id:
            op_log = self.get({'id': log_id})
        if op_log is not None:
            other_params = {}
            data = {'doc': {}}
            raw_after = op_log.get('after') or {}
            raw_before = op_log.get('before') or {}
            raw_before.update(before)
            raw_after.update(after)
            data['doc']['before'] = raw_before
            data['doc']['after'] = raw_after
            if self.version == 7:
                other_params = {'doc_type': self.doc_type}
            return self.es.update(
                index=self.index, id=op_log.get('es_id'), body=data,
                refresh=True, **other_params
            )
        else:
            return super().save(**kwargs)


class LoginLogStore(BaseLogStorage):
    model = UserLoginLog

    def __init__(self, config):
        properties = {
            'id': {'type': 'keyword'},
            'username': {'type': 'keyword'},
            'type': {'type': 'keyword'},
            'ip': {'type': 'keyword'},
            'city': {'type': 'keyword'},
            'backend': {'type': 'keyword'},
            'org_id': {'type': 'keyword'},
            'datetime': {'type': 'date', 'format': 'yyyy-MM-dd HH:mm:ss'}
        }
        keyword_fields = {k for k, v in properties.items() if v.get('type') == 'keyword'}
        exact_fields = keyword_fields | {'datetime'}
        if not config.get('INDEX', None):
            config['INDEX'] = 'jumpserver_login_log'
        else:
            config['INDEX'] = f"{config['INDEX']}_login_log"
        super().__init__(config, properties, keyword_fields, exact_fields)


class FTPLogStore(BaseLogStorage):
    model = FTPLog
    date_field_name = 'date_start'

    def __init__(self, config):
        properties = {
            'id': {'type': 'keyword'},
            'user': {'type': 'keyword'},
            'asset': {'type': 'keyword'},
            'account': {'type': 'keyword'},
            'remote_addr': {'type': 'keyword'},
            'session': {'type': 'keyword'},
            'operate': {'type': 'keyword'},
            'org_id': {'type': 'keyword'},
            'date_start': {'type': 'date', 'format': 'yyyy-MM-dd HH:mm:ss'},
        }
        keyword_fields = {k for k, v in properties.items() if v.get('type') == 'keyword'}
        exact_fields = keyword_fields | {'date_start'}
        if not config.get('INDEX', None):
            config['INDEX'] = 'jumpserver_ftp_log'
        else:
            config['INDEX'] = f"{config['INDEX']}_ftp_log"
        super().__init__(config, properties, keyword_fields, exact_fields=exact_fields)


class PasswordChangeLogStore(BaseLogStorage):
    model = PasswordChangeLog

    def __init__(self, config):
        properties = {
            'id': {'type': 'keyword'},
            'user': {'type': 'keyword'},
            'change_by': {'type': 'keyword'},
            'remote_addr': {'type': 'keyword'},
            'org_id': {'type': 'keyword'},
            'datetime': {'type': 'date', 'format': 'yyyy-MM-dd HH:mm:ss'}
        }
        keyword_fields = {'id', 'user', 'change_by', 'remote_addr', 'org_id'}
        exact_fields = keyword_fields
        if not config.get('INDEX', None):
            config['INDEX'] = 'jumpserver_password_change_log'
        else:
            config['INDEX'] = f"{config['INDEX']}_password_change_log"
        super().__init__(config, properties, keyword_fields, exact_fields)
