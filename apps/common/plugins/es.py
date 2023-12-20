# -*- coding: utf-8 -*-
#
import datetime
import inspect
import sys

if sys.version_info.major == 3 and sys.version_info.minor >= 10:
    from collections.abc import Iterable
else:
    from collections import Iterable
from functools import reduce, partial
from itertools import groupby
from uuid import UUID

from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet as DJQuerySet
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from elasticsearch.exceptions import RequestError, NotFoundError

from common.utils.common import lazyproperty
from common.utils import get_logger
from common.utils.timezone import local_now_date_display
from common.exceptions import JMSException

logger = get_logger(__file__)


class InvalidElasticsearch(JMSException):
    default_code = 'invalid_elasticsearch'
    default_detail = _('Invalid elasticsearch config')


class NotSupportElasticsearch8(JMSException):
    default_code = 'not_support_elasticsearch8'
    default_detail = _('Not Support Elasticsearch8')


class ES(object):
    def __init__(self, config, properties, keyword_fields, exact_fields=None, match_fields=None):

        self.config = config
        hosts = self.config.get('HOSTS')
        kwargs = self.config.get('OTHER', {})

        ignore_verify_certs = kwargs.pop('IGNORE_VERIFY_CERTS', False)
        if ignore_verify_certs:
            kwargs['verify_certs'] = None
        self.es = Elasticsearch(hosts=hosts, max_retries=0, **kwargs)
        self.index_prefix = self.config.get('INDEX') or 'jumpserver'
        self.is_index_by_date = bool(self.config.get('INDEX_BY_DATE', False))

        self.index = None
        self.query_index = None
        self.properties = properties
        self.exact_fields, self.match_fields, self.keyword_fields = set(), set(), set()

        if isinstance(keyword_fields, Iterable):
            self.keyword_fields.update(keyword_fields)
        if isinstance(exact_fields, Iterable):
            self.exact_fields.update(exact_fields)
        if isinstance(match_fields, Iterable):
            self.match_fields.update(match_fields)

        self.init_index()
        self.doc_type = self.config.get("DOC_TYPE") or '_doc'
        if self.is_new_index_type():
            self.doc_type = '_doc'
            self.exact_fields.update(self.keyword_fields)
        else:
            self.match_fields.update(self.keyword_fields)

    def init_index(self):
        if self.is_index_by_date:
            date = local_now_date_display()
            self.index = '%s-%s' % (self.index_prefix, date)
            self.query_index = '%s-alias' % self.index_prefix
        else:
            self.index = self.config.get("INDEX") or 'jumpserver'
            self.query_index = self.config.get("INDEX") or 'jumpserver'

    def is_new_index_type(self):
        if not self.ping(timeout=2):
            return False

        info = self.es.info()
        version = info['version']['number'].split('.')[0]

        if version == '8':
            raise NotSupportElasticsearch8

        try:
            # 获取索引信息，如果没有定义，直接返回
            data = self.es.indices.get_mapping(index=self.index)
        except NotFoundError:
            return False

        try:
            if version == '6':
                # 检测索引是不是新的类型 es6
                properties = data[self.index]['mappings']['data']['properties']
            else:
                # 检测索引是不是新的类型 es7 default index type: _doc
                properties = data[self.index]['mappings']['properties']

            for keyword in self.keyword_fields:
                if not properties[keyword]['type'] == 'keyword':
                    break
            else:
                return True
        except KeyError:
            return False

    def pre_use_check(self):
        if not self.ping(timeout=3):
            raise InvalidElasticsearch
        self._ensure_index_exists()

    def _ensure_index_exists(self):
        try:
            info = self.es.info()
            version = info['version']['number'].split('.')[0]
            if version == '6':
                mappings = {'mappings': {'data': {'properties': self.properties}}}
            else:
                mappings = {'mappings': {'properties': self.properties}}

            if self.is_index_by_date:
                mappings['aliases'] = {
                    self.query_index: {}
                }

            try:
                self.es.indices.create(index=self.index, body=mappings)
            except RequestError as e:
                if e.error == 'resource_already_exists_exception':
                    logger.warning(e)
                else:
                    logger.exception(e)
        except Exception as e:
            logger.error(e, exc_info=True)

    def make_data(self, data):
        return []

    def save(self, **kwargs):
        data = self.make_data(kwargs)
        return self.es.index(index=self.index, doc_type=self.doc_type, body=data)

    def bulk_save(self, command_set, raise_on_error=True):
        actions = []
        for command in command_set:
            data = dict(
                _index=self.index,
                _type=self.doc_type,
                _source=self.make_data(command),
            )
            actions.append(data)
        return bulk(self.es, actions, index=self.index, raise_on_error=raise_on_error)

    def get(self, query: dict):
        item = None
        data = self.filter(query, size=1)
        if len(data) >= 1:
            item = data[0]
        return item

    def filter(self, query: dict, from_=None, size=None, sort=None):
        try:
            data = self._filter(query, from_, size, sort)
        except Exception as e:
            logger.error('ES filter error: {}'.format(e))
            data = []
        return data

    def _filter(self, query: dict, from_=None, size=None, sort=None):
        body = self.get_query_body(**query)

        data = self.es.search(
            index=self.query_index, body=body,
            from_=from_, size=size, sort=sort
        )

        source_data = []
        for item in data['hits']['hits']:
            if item:
                item['_source'].update({'es_id': item['_id']})
                source_data.append(item['_source'])

        return source_data

    def count(self, **query):
        try:
            body = self.get_query_body(**query)
            data = self.es.count(index=self.query_index, body=body)
            count = data["count"]
        except Exception as e:
            logger.error('ES count error: {}'.format(e))
            count = 0
        return count

    def __getattr__(self, item):
        return getattr(self.es, item)

    def all(self):
        """返回所有数据"""
        raise NotImplementedError("Not support")

    def ping(self, timeout=None):
        try:
            return self.es.ping(request_timeout=timeout)
        except Exception:
            return False

    @staticmethod
    def handler_time_field(data):
        datetime__gte = data.get('datetime__gte')
        datetime__lte = data.get('datetime__lte')
        datetime_range = {}

        if datetime__gte:
            if isinstance(datetime__gte, datetime.datetime):
                datetime__gte = datetime__gte.strftime('%Y-%m-%d %H:%M:%S')
            datetime_range['gte'] = datetime__gte
        if datetime__lte:
            if isinstance(datetime__lte, datetime.datetime):
                datetime__lte = datetime__lte.strftime('%Y-%m-%d %H:%M:%S')
            datetime_range['lte'] = datetime__lte
        return 'datetime', datetime_range

    @staticmethod
    def handle_exact_fields(exact):
        _filter = []
        for k, v in exact.items():
            query = 'term'
            if isinstance(v, list):
                query = 'terms'
            _filter.append({
                query: {k: v}
            })
        return _filter

    def get_query_body(self, **kwargs):
        new_kwargs = {}
        for k, v in kwargs.items():
            if isinstance(v, UUID):
                v = str(v)
            if k == 'pk':
                k = 'id'
            if k.endswith('__in'):
                k = k.replace('__in', '')
            new_kwargs[k] = v
        kwargs = new_kwargs

        index_in_field = 'id__in'
        exact_fields = self.exact_fields
        match_fields = self.match_fields

        match = {}
        exact = {}
        index = {}

        if index_in_field in kwargs:
            index['values'] = kwargs[index_in_field]

        for k, v in kwargs.items():
            if k in exact_fields:
                exact[k] = v
            elif k in match_fields:
                match[k] = v

        # 处理时间
        time_field_name, time_range = self.handler_time_field(kwargs)

        # 处理组织
        should = []
        org_id = match.get('org_id')

        real_default_org_id = '00000000-0000-0000-0000-000000000002'
        root_org_id = '00000000-0000-0000-0000-000000000000'

        if org_id == root_org_id:
            match.pop('org_id')
        elif org_id in (real_default_org_id, ''):
            match.pop('org_id')
            should.append({
                'bool': {
                    'must_not': [
                        {
                            'wildcard': {'org_id': '*'}
                        }
                    ]}
            })
            should.append({'match': {'org_id': real_default_org_id}})

        # 构建 body
        body = {
            'query': {
                'bool': {
                    'must': [
                        {'match': {k: v}} for k, v in match.items()
                    ],
                    'should': should,
                    'filter': self.handle_exact_fields(exact) +
                              [
                                  {
                                      'range': {
                                          time_field_name: time_range
                                      }
                                  }
                              ] + [
                                  {
                                      'ids': {k: v}
                                  } for k, v in index.items()
                              ]
                }
            },
        }
        return body


class QuerySet(DJQuerySet):
    default_days_ago = 7
    max_result_window = 10000

    def __init__(self, es_instance):
        self._method_calls = []
        self._slice = None  # (from_, size)
        self._storage = es_instance

        # 命令列表模糊搜索时报错
        super().__init__()

    @lazyproperty
    def _grouped_method_calls(self):
        _method_calls = {k: list(v) for k, v in groupby(self._method_calls, lambda x: x[0])}
        return _method_calls

    @lazyproperty
    def _filter_kwargs(self):
        _method_calls = self._grouped_method_calls
        filter_calls = _method_calls.get('filter')
        if not filter_calls:
            return {}
        names, multi_args, multi_kwargs = zip(*filter_calls)
        kwargs = reduce(lambda x, y: {**x, **y}, multi_kwargs, {})

        striped_kwargs = {}
        for k, v in kwargs.items():
            k = k.replace('__exact', '')
            k = k.replace('__startswith', '')
            k = k.replace('__icontains', '')
            striped_kwargs[k] = v
        return striped_kwargs

    @lazyproperty
    def _sort(self):
        order_by = self._grouped_method_calls.get('order_by')
        if order_by:
            for call in reversed(order_by):
                fields = call[1]
                if fields:
                    field = fields[-1]

                    if field.startswith('-'):
                        direction = 'desc'
                    else:
                        direction = 'asc'
                    field = field.lstrip('-+')
                    sort = f'{field}:{direction}'
                    return sort

    def __execute(self):
        _filter_kwargs = self._filter_kwargs
        _sort = self._sort
        from_, size = self._slice or (None, None)
        data = self._storage.filter(_filter_kwargs, from_=from_, size=size, sort=_sort)
        return self.model.from_multi_dict(data)

    def __stage_method_call(self, item, *args, **kwargs):
        _clone = self.__clone()
        _clone._method_calls.append((item, args, kwargs))
        return _clone

    def __clone(self):
        uqs = QuerySet(self._storage)
        uqs._method_calls = self._method_calls.copy()
        uqs._slice = self._slice
        uqs.model = self.model
        return uqs

    def get(self, **kwargs):
        kwargs.update(self._filter_kwargs)
        return self._storage.get(kwargs)

    def count(self, limit_to_max_result_window=True):
        filter_kwargs = self._filter_kwargs
        count = self._storage.count(**filter_kwargs)
        if limit_to_max_result_window:
            count = min(count, self.max_result_window)
        return count

    def __getattribute__(self, item):
        if any((
                item.startswith('__'),
                item in QuerySet.__dict__,
        )):
            return object.__getattribute__(self, item)

        origin_attr = object.__getattribute__(self, item)
        if not inspect.ismethod(origin_attr):
            return origin_attr

        attr = partial(self.__stage_method_call, item)
        return attr

    def __getitem__(self, item):
        max_window = self.max_result_window
        if isinstance(item, slice):
            if self._slice is None:
                clone = self.__clone()
                from_ = item.start or 0
                if item.stop is None:
                    size = self.max_result_window - from_
                else:
                    size = item.stop - from_

                if from_ + size > max_window:
                    if from_ >= max_window:
                        from_ = max_window
                        size = 0
                    else:
                        size = max_window - from_
                clone._slice = (from_, size)
                return clone
        return self.__execute()[item]

    def __repr__(self):
        return self.__execute().__repr__()

    def __iter__(self):
        return iter(self.__execute())

    def __len__(self):
        return self.count()
