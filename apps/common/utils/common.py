# -*- coding: utf-8 -*-
#
import re
import data_tree
from collections import OrderedDict
from itertools import chain
import logging
import datetime
import uuid
from functools import wraps
import time
import ipaddress
import psutil
from django.utils.translation import ugettext_lazy as _
from ..exceptions import JMSException


UUID_PATTERN = re.compile(r'\w{8}(-\w{4}){3}-\w{12}')
ipip_db = None


def combine_seq(s1, s2, callback=None):
    for s in (s1, s2):
        if not hasattr(s, '__iter__'):
            return []

    seq = chain(s1, s2)
    if callback:
        seq = map(callback, seq)
    return seq


def get_logger(name=''):
    return logging.getLogger('jumpserver.%s' % name)


def get_syslogger(name=''):
    return logging.getLogger('syslog.%s' % name)


def timesince(dt, since='', default="just now"):
    """
    Returns string representing "time since" e.g.
    3 days, 5 hours.
    """

    if not since:
        since = datetime.datetime.utcnow()

    if since is None:
        return default

    diff = since - dt

    periods = (
        (diff.days / 365, "year", "years"),
        (diff.days / 30, "month", "months"),
        (diff.days / 7, "week", "weeks"),
        (diff.days, "day", "days"),
        (diff.seconds / 3600, "hour", "hours"),
        (diff.seconds / 60, "minute", "minutes"),
        (diff.seconds, "second", "seconds"),
    )

    for period, singular, plural in periods:
        if period:
            return "%d %s" % (period, singular if period == 1 else plural)
    return default


def setattr_bulk(seq, key, value):
    def set_attr(obj):
        setattr(obj, key, value)
        return obj
    return map(set_attr, seq)


def set_or_append_attr_bulk(seq, key, value):
    for obj in seq:
        ori = getattr(obj, key, None)
        if ori:
            value += " " + ori
        setattr(obj, key, value)


def capacity_convert(size, expect='auto', rate=1000):
    """
    :param size: '100MB', '1G'
    :param expect: 'K, M, G, T
    :param rate: Default 1000, may be 1024
    :return:
    """
    rate_mapping = (
        ('K', rate),
        ('KB', rate),
        ('M', rate**2),
        ('MB', rate**2),
        ('G', rate**3),
        ('GB', rate**3),
        ('T', rate**4),
        ('TB', rate**4),
    )

    rate_mapping = OrderedDict(rate_mapping)

    std_size = 0  # To KB
    for unit in rate_mapping:
        if size.endswith(unit):
            try:
                std_size = float(size.strip(unit).strip()) * rate_mapping[unit]
            except ValueError:
                pass

    if expect == 'auto':
        for unit, rate_ in rate_mapping.items():
            if rate > std_size/rate_ >= 1 or unit == "T":
                expect = unit
                break

    if expect not in rate_mapping:
        expect = 'K'

    expect_size = std_size / rate_mapping[expect]
    return expect_size, expect


def sum_capacity(cap_list):
    total = 0
    for cap in cap_list:
        size, _ = capacity_convert(cap, expect='K')
        total += size
    total = '{} K'.format(total)
    return capacity_convert(total, expect='auto')


def get_short_uuid_str():
    return str(uuid.uuid4()).split('-')[-1]


def is_uuid(seq):
    if isinstance(seq, uuid.UUID):
        return True
    elif isinstance(seq, str) and UUID_PATTERN.match(seq):
        return True
    elif isinstance(seq, (list, tuple)):
        all([is_uuid(x) for x in seq])
    return False


def get_request_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')

    if x_forwarded_for and x_forwarded_for[0]:
        login_ip = x_forwarded_for[0]
    else:
        login_ip = request.META.get('REMOTE_ADDR', '')
    return login_ip


def get_request_ip_or_data(request):
    ip = ''
    if hasattr(request, 'data'):
        ip = request.data.get('remote_addr', '')
    ip = ip or get_request_ip(request)
    return ip


def get_request_user_agent(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    return user_agent


def validate_ip(ip):
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        pass
    return False


def with_cache(func):
    cache = {}
    key = "_{}.{}".format(func.__module__, func.__name__)

    @wraps(func)
    def wrapper(*args, **kwargs):
        cached = cache.get(key)
        if cached:
            return cached
        res = func(*args, **kwargs)
        cache[key] = res
        return res
    return wrapper


def random_string(length):
    import string
    import random
    charset = string.ascii_letters + string.digits
    s = [random.choice(charset) for i in range(length)]
    return ''.join(s)


logger = get_logger(__name__)


def timeit(func):
    def wrapper(*args, **kwargs):
        if hasattr(func, '__name__'):
            name = func.__name__
        else:
            name = func
        logger.debug("Start call: {}".format(name))
        now = time.time()
        result = func(*args, **kwargs)
        using = (time.time() - now) * 1000
        msg = "End call {}, using: {:.1f}ms".format(name, using)
        logger.debug(msg)
        return result
    return wrapper


def group_obj_by_count(objs, count=50):
    objs_grouped = [
        objs[i:i + count] for i in range(0, len(objs), count)
    ]
    return objs_grouped


def dict_get_any(d, keys):
    for key in keys:
        value = d.get(key)
        if value:
            return value
    return None


class lazyproperty:
    def __init__(self, func):
        self.func = func

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            value = self.func(instance)
            setattr(instance, self.func.__name__, value)
            return value


def get_disk_usage():
    partitions = psutil.disk_partitions()
    mount_points = [p.mountpoint for p in partitions]
    usages = {p: psutil.disk_usage(p) for p in mount_points}
    return usages


# Verify that `value` is in `choices` and throw an `JMSException`
# ---------------------------------------------------------------


def check_value_in_choices(value, choices, **kwargs):
    # get raise parameters from kwargs
    raise_exception = kwargs.get('raise_exception', False)
    raise_error_msg = kwargs.get('raise_error_msg', None)
    raise_reverse = kwargs.get('raise_reverse', False)

    def should_raise():
        """
        Simplify the following logic:

        if raise_exception:
            if raise_reverse and value_in_choices:
                return True
            else:
                return False

            if not raise_reverse and not value_in_choices:
                return True
            else:
                return False
        else:
            return False
        """
        return raise_exception and raise_reverse == value_in_choices

    value_in_choices = True if value in choices else False

    if not should_raise():
        return value_in_choices

    if raise_error_msg is None:
        raise_error_msg = _('Value `{}` is not in Choices: `{}`'.format(value, choices))

    raise JMSException(raise_error_msg)


# Quick lookup dict
# -----------------


class QuickLookupDict(object):
    """
    说明:
        dict 类型数据的快速查找
    作用:
        可根据指定 key 的深度 path 快速查找出对应的 value 值
    依赖:
        data-tree==0.0.1
    实现:
        通过对 data-tree 库的封装来实现
    """

    def __init__(self, data, key_delimiter='.'):
        self._check_data_type(data, type_choices=(dict, ), error='Expected `data` type is dict')
        self.data = data
        self.key_delimiter = key_delimiter
        self._data_tree = self._get_data_tree(data, key_delimiter)

    # Method encapsulated of `data-tree`
    # ----------------------------------

    @staticmethod
    def _get_data_tree(data, key_delimiter):
        tree = data_tree.Data_tree_node(
            arg_data=data, arg_string_delimiter_for_path=key_delimiter
        )
        return tree

    def _get_data_tree_node(self, path):
        return self._data_tree.get(arg_path=path)

    @staticmethod
    def _get_data_tree_node_original_data(tree_node):
        if isinstance(tree_node, data_tree.Data_tree_node):
            data = tree_node.get_data_in_format_for_export()
        else:
            data = tree_node
        return data

    # Method called internally
    # ------------------------

    @staticmethod
    def _check_data_type(data, type_choices, error=None):
        error = error or '`data` type error, {} => {}'.format(type(data), type_choices)
        assert isinstance(data, type_choices), error

    @staticmethod
    def _check_object_callable(_object):
        if _object is None:
            return False
        if not callable(_object):
            return False
        return True

    # Method called externally
    # ------------------------

    def get(self, key_path, default=None):
        error = 'key_path - can be either a list of keys, or a delimited string.'
        self._check_data_type(key_path, (list, str,), error=error)

        tree_node = self._get_data_tree_node(key_path)
        if tree_node is None:
            return default
        value = self._get_data_tree_node_original_data(tree_node)
        return value

    def get_many(self, key_paths, default=None):
        values = [
            self.get(key_path, default=default) for key_path in key_paths
        ]
        return values

    def find_one(self, key_paths, default=None, callable_filter=None):
        """
        按照 key_paths 顺序查找，返回第一个满足 `callable_filter` 规则的值
        """

        def get_data_filter():
            if self._check_object_callable(callable_filter):
                return callable_filter
            return self.__default_find_callable_filter

        _filter = get_data_filter()

        for key_path in key_paths:
            value = self.get(key_path=key_path)
            if _filter(key_path, value):
                return value

        return default

    # Method default
    # --------------

    @staticmethod
    def __default_find_callable_filter(key_path, value):
        return value is not None




