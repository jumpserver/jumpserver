# -*- coding: utf-8 -*-
#
import datetime
import json
import inspect
import warnings

from typing import Iterable, Sequence
from functools import partial
from uuid import UUID

from django.utils.translation import gettext_lazy as _
from django.db.models import QuerySet as DJQuerySet, Q
from elasticsearch7 import Elasticsearch
from elasticsearch7.helpers import bulk
from elasticsearch7.exceptions import RequestError, SSLError, ElasticsearchWarning
from elasticsearch7.exceptions import NotFoundError as NotFoundError7

from elasticsearch8.exceptions import NotFoundError as NotFoundError8
from elasticsearch8.exceptions import BadRequestError

from common.db.encoder import ModelJSONFieldEncoder
from common.utils.common import lazyproperty
from common.utils import get_logger
from common.utils.timezone import local_now_date_display
from common.exceptions import JMSException, JMSObjectDoesNotExist

warnings.filterwarnings("ignore", category=ElasticsearchWarning)

logger = get_logger(__file__)


class InvalidElasticsearch(JMSException):
    default_code = 'invalid_elasticsearch'
    default_detail = _('Invalid elasticsearch config')


class NotSupportElasticsearch8(JMSException):
    default_code = 'not_support_elasticsearch8'
    default_detail = _('Not Support Elasticsearch8')


class InvalidElasticsearchSSL(JMSException):
    default_code = 'invalid_elasticsearch_SSL'
    default_detail = _(
        'Connection failed: Self-signed certificate used. Please check server certificate configuration')


class ESClient(object):

    def __new__(cls, *args, **kwargs):
        version = get_es_client_version(**kwargs)
        if version == 6:
            return ESClientV6(*args, **kwargs)
        if version == 7:
            return ESClientV7(*args, **kwargs)
        elif version == 8:
            return ESClientV8(*args, **kwargs)
        raise ValueError('Unsupported ES_VERSION %r' % version)


class ESClientBase(object):
    VERSION = 0

    @classmethod
    def get_properties(cls, data, index):
        return data[index]['mappings']['properties']

    @classmethod
    def get_mapping(cls, properties):
        return {'mappings': {'properties': properties}}


class ESClientV7(ESClientBase):
    VERSION = 7

    def __init__(self, *args, **kwargs):
        from elasticsearch7 import Elasticsearch
        self.es = Elasticsearch(*args, **kwargs)

    @classmethod
    def get_sort(cls, field, direction):
        return f'{field}:{direction}'


class ESClientV6(ESClientV7):
    VERSION = 6

    @classmethod
    def get_properties(cls, data, index):
        return data[index]['mappings']['data']['properties']

    @classmethod
    def get_mapping(cls, properties):
        return {'mappings': {'data': {'properties': properties}}}


class ESClientV8(ESClientBase):
    VERSION = 8

    def __init__(self, *args, **kwargs):
        from elasticsearch8 import Elasticsearch
        self.es = Elasticsearch(*args, **kwargs)

    @classmethod
    def get_sort(cls, field, direction):
        return {field: {'order': direction}}


def get_es_client_version(**kwargs):
    try:
        es = Elasticsearch(**kwargs)
        info = es.info()
        version = int(info['version']['number'].split('.')[0])
        return version
    except SSLError:
        raise InvalidElasticsearchSSL
    except Exception:
        raise InvalidElasticsearch


class ES(object):

    def __init__(self, config, properties, keyword_fields, exact_fields=None, match_fields=None):
        self.config = config
        hosts = self.config.get('HOSTS')
        kwargs = self.config.get('OTHER', {})

        ignore_verify_certs = kwargs.pop('IGNORE_VERIFY_CERTS', False)
        if ignore_verify_certs:
            kwargs['verify_certs'] = None
        self.client = ESClient(hosts=hosts, max_retries=0, **kwargs)
        self.es = self.client.es
        self.version = self.client.VERSION
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

        try:
            # 获取索引信息，如果没有定义，直接返回
            data = self.es.indices.get_mapping(index=self.index)
        except (NotFoundError8, NotFoundError7):
            return False

        try:
            properties = self.client.get_properties(data=data, index=self.index)
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
            mappings = self.client.get_mapping(self.properties)

            if self.is_index_by_date:
                mappings['aliases'] = {
                    self.query_index: {}
                }
            if self.es.indices.exists(index=self.index):
                return
            try:
                self.es.indices.create(index=self.index, body=mappings)
            except (RequestError, BadRequestError) as e:
                if e.error == 'resource_already_exists_exception':
                    logger.warning(e)
                else:
                    logger.exception(e)
        except Exception as e:
            logger.error(e, exc_info=True)

    def make_data(self, data):
        return {}

    def save(self, **kwargs):
        other_params = {}
        data = self.make_data(kwargs)
        if self.version == 7:
            other_params = {'doc_type': self.doc_type}
        return self.es.index(index=self.index, body=data, refresh=True, **other_params)

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

    def filter(self, query: dict, from_=None, size=None, sort=None, fields=None):
        try:
            from_, size = from_ or 0, size or 1
            data = self._filter(query, from_, size, sort, fields)
        except Exception as e:
            logger.error('ES filter error: {}'.format(e))
            data = []
        return data

    def _filter(self, query: dict, from_=None, size=None, sort=None, fields=None):
        body = self._get_query_body(query, fields)
        search_params = {
            'index': self.query_index, 'body': body, 'from_': from_, 'size': size
        }
        if sort is not None:
            search_params['sort'] = sort
        data = self.es.search(**search_params)

        source_data = []
        for item in data['hits']['hits']:
            if item:
                item['_source'].update({'es_id': item['_id']})
                source_data.append(item['_source'])

        return source_data

    def count(self, **query):
        try:
            body = self._get_query_body(query_params=query)
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
        except Exception:  # noqa
            return False

    def _get_date_field_name(self):
        date_field_name = ''
        for name, attr in self.properties.items():
            if attr.get('type', '') == 'date':
                date_field_name = name
                break
        return date_field_name

    def handler_time_field(self, data):
        date_field_name = getattr(self, 'date_field_name', 'datetime')
        datetime__gte = data.get(f'{date_field_name}__gte')
        datetime__lte = data.get(f'{date_field_name}__lte')
        datetime__range = data.get(f'{date_field_name}__range')
        if isinstance(datetime__range, Sequence) and len(datetime__range) == 2:
            datetime__gte = datetime__gte or datetime__range[0]
            datetime__lte = datetime__lte or datetime__range[1]

        datetime_range = {}
        if datetime__gte:
            if isinstance(datetime__gte, (datetime.datetime, datetime.date)):
                datetime__gte = datetime__gte.strftime('%Y-%m-%d %H:%M:%S')
            datetime_range['gte'] = datetime__gte
        if datetime__lte:
            if isinstance(datetime__lte, (datetime.datetime, datetime.date)):
                datetime__lte = datetime__lte.strftime('%Y-%m-%d %H:%M:%S')
            datetime_range['lte'] = datetime__lte
        return date_field_name, datetime_range

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

    @staticmethod
    def __handle_field(key, value):
        if isinstance(value, UUID):
            value = str(value)
        if key == 'pk':
            key = 'id'
        if key.endswith('__in'):
            key = key.replace('__in', '')
        return key, value

    def __build_special_query_body(self, query_kwargs):
        match, exact = {}, {}
        for k, v in query_kwargs.items():
            k, v = self.__handle_field(k, v)
            if k in self.exact_fields:
                exact[k] = v
            elif k in self.match_fields:
                match[k] = v

        result = self.handle_exact_fields(exact) + [
            {'match': {k: v}} for k, v in match.items()
        ]
        return result

    def _get_query_body(self, query_params=None, fields=None):
        query_params = query_params or {}
        not_kwargs = query_params.pop('__not', {})
        or_kwargs = query_params.pop('__or', {})
        new_kwargs = {}
        for k, v in query_params.items():
            k, v = self.__handle_field(k, v)
            new_kwargs[k] = v
        kwargs = new_kwargs

        index_in_field = 'id__in'
        match, exact, index = {}, {}, {}

        if index_in_field in kwargs:
            index['values'] = kwargs[index_in_field]

        for k, v in kwargs.items():
            if k in self.exact_fields:
                exact[k] = v
            elif k in self.match_fields:
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
                    'must_not': self.__build_special_query_body(not_kwargs),
                    'must': [
                                {'match': {k: v}} for k, v in match.items()
                            ] + self.handle_exact_fields(exact),
                    'should': should + self.__build_special_query_body(or_kwargs),
                    'filter': [
                                  {'range': {time_field_name: time_range}}
                              ] + [
                                  {'ids': {k: v}} for k, v in index.items()
                              ]
                }
            },
        }
        if len(body['query']['bool']['should']) > 0:
            body['query']['bool']['minimum_should_match'] = 1
        body = self.part_fields_query(body, fields)
        return json.loads(json.dumps(body, cls=ModelJSONFieldEncoder))

    @staticmethod
    def part_fields_query(body, fields):
        if not fields:
            return body
        body['_source'] = list(fields)
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
        _method_calls = {}
        for sub_action, sub_args, sub_kwargs in self._method_calls:
            args, kwargs = _method_calls.get(sub_action, ([], {}))
            args.extend(sub_args)
            kwargs.update(sub_kwargs)
            _method_calls[sub_action] = (args, kwargs)
        return _method_calls

    def _merge_kwargs(self, filter_args, exclude_args, filter_kwargs, exclude_kwargs):
        or_filter = {}
        for f_arg in filter_args:
            if f_arg.connector == Q.OR:
                or_filter.update({c[0]: c[1] for c in f_arg.children})
        filter_kwargs['__or'] = self.striped_kwargs(or_filter)
        filter_kwargs['__not'] = self.striped_kwargs(exclude_kwargs)
        return self.striped_kwargs(filter_kwargs)

    @staticmethod
    def striped_kwargs(kwargs):
        striped_kwargs = {}
        for k, v in kwargs.items():
            k = k.replace('__exact', '')
            k = k.replace('__startswith', '')
            k = k.replace('__icontains', '')
            striped_kwargs[k] = v
        return striped_kwargs

    @lazyproperty
    def _filter_kwargs(self):
        f_args, f_kwargs = self._grouped_method_calls.get('filter', ((), {}))
        e_args, e_kwargs = self._grouped_method_calls.get('exclude', ((), {}))
        if not f_kwargs and not e_kwargs:
            return {}
        return self._merge_kwargs(f_args, e_args, f_kwargs, e_kwargs)

    @lazyproperty
    def _sort(self):
        order_by = self._grouped_method_calls.get('order_by', ((), {}))[0]
        for field in order_by:
            if field.startswith('-'):
                direction = 'desc'
            else:
                direction = 'asc'
            field = field.lstrip('-+')
            sort = self._storage.client.get_sort(field, direction)
            return sort

    def __execute(self):
        _vl_args, _vl_kwargs = self._grouped_method_calls.get('values_list', ((), {}))
        from_, size = self._slice or (0, 20)
        data = self._storage.filter(
            self._filter_kwargs, from_=from_, size=size, sort=self._sort, fields=_vl_args
        )
        return self.model.from_multi_dict(data, flat=bool(_vl_args))

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

    def first(self):
        self._slice = (0, 1)
        data = self.__execute()
        return self.model.from_dict(data[0]) if data else None

    def get(self, **kwargs):
        kwargs.update(self._filter_kwargs)
        item = self._storage.get(kwargs)
        if not item:
            raise JMSObjectDoesNotExist(
                object_name=self.model._meta.verbose_name  # noqa
            )
        return self.model.from_dict(item)

    def count(self, limit_to_max_result_window=True):
        count = self._storage.count(**self._filter_kwargs)
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
