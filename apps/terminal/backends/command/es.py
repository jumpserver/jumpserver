# -*- coding: utf-8 -*-
#
from datetime import datetime

import pytz

from elasticsearch8.helpers import bulk as bulk8

from common.plugins.es import ES, ESClientV6, ESClientV8, bulk, RequestError, BadRequestError
from common.utils import get_logger

logger = get_logger(__file__)


class CommandStore(ES):
    supports_idempotent_receipts = True

    def bulk_save(self, commands, raise_on_error=True):
        commands = list(commands)
        if not any(command.get('id') for command in commands):
            return super().bulk_save(commands, raise_on_error=raise_on_error)
        actions = []
        for command in commands:
            index = self.index
            if command.get('id') and self.is_index_by_date:
                # Routing by upload day would duplicate a retried event after
                # midnight/restart. Receipt events always use their UTC day.
                date = datetime.fromtimestamp(command['timestamp'], tz=pytz.UTC).strftime('%Y-%m-%d')
                index = f'{self.index_prefix}-{date}'
            self._ensure_receipt_index(index)
            action = dict(_index=index, _source=self.make_data(command))
            if isinstance(self.client, ESClientV6):
                action['_type'] = self.doc_type
            if command.get('id'):
                action['_id'] = str(command['id'])
            actions.append(action)
        save = bulk8 if isinstance(self.client, ESClientV8) else bulk
        count, errors = save(self.es, actions, raise_on_error=raise_on_error)
        return count == len(commands) and not errors

    def _ensure_receipt_index(self, index):
        if index in self._receipt_indices:
            return
        mappings = self.client.get_mapping(self.properties)
        if self.is_index_by_date:
            mappings['aliases'] = {self.query_index: {}}
        try:
            self.es.indices.create(index=index, body=mappings)
        except (RequestError, BadRequestError) as exc:
            if exc.error != 'resource_already_exists_exception':
                raise
        self._receipt_indices.add(index)

    def __init__(self, config):
        properties = {
            "session": {
                "type": "keyword"
            },
            "org_id": {
                "type": "keyword"
            },
            "@timestamp": {
                "type": "date"
            },
            "timestamp": {
                "type": "long"
            }
        }
        exact_fields = {'risk_level'}
        fuzzy_fields = {'input', 'user', 'asset', 'account'}
        match_fields = {'input'}
        keyword_fields = {'session', 'org_id'}

        super().__init__(config, properties, keyword_fields, exact_fields, fuzzy_fields, match_fields)
        self._receipt_indices = set()

    @staticmethod
    def make_data(command):
        data = dict(
            user=command["user"], asset=command["asset"],
            account=command["account"], input=command["input"],
            output=command["output"], risk_level=command["risk_level"],
            session=command["session"], timestamp=command["timestamp"],
            org_id=command["org_id"]
        )
        data["date"] = datetime.fromtimestamp(command['timestamp'], tz=pytz.UTC)
        return data

    @staticmethod
    def handler_time_field(data):
        timestamp__gte = data.get('timestamp__gte')
        timestamp__lte = data.get('timestamp__lte')
        timestamp_range = {}

        if timestamp__gte:
            timestamp_range['gte'] = timestamp__gte
        if timestamp__lte:
            timestamp_range['lte'] = timestamp__lte
        return 'timestamp', timestamp_range
