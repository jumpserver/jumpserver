# -*- coding: utf-8 -*-
#
import uuid

from django.utils.translation import gettext_lazy as _

from common.utils.timezone import local_now_display
from common.utils import get_logger
from common.plugins.es import ES
from .base import BaseOperateStorage

logger = get_logger(__file__)


class OperateLogStore(BaseOperateStorage, ES):
    def __init__(self, config):
        properties = {
            "id": {
                "type": "keyword"
            },
            "user": {
                "type": "keyword"
            },
            "action": {
                "type": "keyword"
            },
            "resource_type": {
                "type": "keyword"
            },
            "org_id": {
                "type": "keyword"
            },
            "datetime": {
                "type": "date",
                "format": "yyyy-MM-dd HH:mm:ss"
            }
        }
        exact_fields = {}
        match_fields = {
            'id', 'user', 'action', 'resource_type',
            'resource', 'remote_addr', 'org_id'
        }
        keyword_fields = {
            'id', 'user', 'action', 'resource_type', 'org_id'
        }
        if not config.get('INDEX'):
            config['INDEX'] = 'jumpserver_operate_log'
        super().__init__(config, properties, keyword_fields, exact_fields, match_fields)
        self.pre_use_check()

    @staticmethod
    def get_type():
        return 'es'

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

    def make_data(self, data):
        op_id = data.get('id', str(uuid.uuid4()))
        datetime_param = data.get('datetime', local_now_display())
        data = {
            'id': op_id, 'user': data['user'], 'action': data['action'],
            'resource_type': data['resource_type'], 'resource': data['resource'],
            'remote_addr': data['remote_addr'], 'datetime': datetime_param,
            'before': data['before'], 'after': data['after'], 'org_id': data['org_id']
        }
        return data

    def save(self, **kwargs):
        log_id = kwargs.get('id', '')
        before = kwargs.get('before') or {}
        after = kwargs.get('after') or {}

        op_log = self.get({'id': log_id})
        if op_log is not None:
            data = {'doc': {}}
            raw_after = op_log.get('after') or {}
            raw_before = op_log.get('before') or {}
            raw_before.update(before)
            raw_after.update(after)
            data['doc']['before'] = raw_before
            data['doc']['after'] = raw_after
            self.es.update(
                index=self.index, doc_type=self.doc_type,
                id=op_log.get('es_id'), body=data, refresh=True
            )
        else:
            data = self.make_data(kwargs)
            self.es.index(
                index=self.index, doc_type=self.doc_type, body=data,
                refresh=True
            )
