# -*- coding: utf-8 -*-
#
from datetime import datetime

import pytz

from common.plugins.es import ES
from common.utils import get_logger
from terminal.const import CommandSourceChoices

logger = get_logger(__file__)


class CommandStore(ES):
    def __init__(self, config):
        properties = {
            "source": {
                "type": "short"
            },
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

    @staticmethod
    def make_data(command):
        data = dict(
            user=command["user"], asset=command["asset"],
            account=command["account"], input=command["input"],
            output=command["output"], risk_level=command["risk_level"],
            session=command["session"], timestamp=command["timestamp"],
            org_id=command["org_id"]
        )
        data['source'] = CommandSourceChoices.from_value(command.get('source'))
        data["date"] = datetime.fromtimestamp(command['timestamp'], tz=pytz.UTC)
        return data

    def get_query_body(self, **kwargs):
        source_lookups = {'source': False, 'source__exact': False, 'source__not': True}
        source_conditions = [
            (kwargs.pop(name), negate)
            for name, negate in source_lookups.items() if name in kwargs
        ]
        search = []
        for query in kwargs.pop('search', []):
            query = query.copy()
            for name, negate in source_lookups.items():
                if name in query:
                    source_conditions.append((query.pop(name), negate))
            if query:
                search.append(query)
        body = super().get_query_body(search=search, **kwargs)
        for value, negate in source_conditions:
            if value is None or value == '':
                continue
            value = CommandSourceChoices.from_value(value)
            condition = {'term': {'source': value}}
            if value == CommandSourceChoices.manual:
                condition = {
                    'bool': {
                        'should': [
                            {'term': {'source': CommandSourceChoices.manual}},
                            {'bool': {'must_not': [{'exists': {'field': 'source'}}]}},
                        ],
                        'minimum_should_match': 1,
                    },
                }
            if negate:
                condition = {'bool': {'must_not': [condition]}}
            body['query']['bool']['filter'].append(condition)
        return body

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
