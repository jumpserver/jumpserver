# -*- coding: utf-8 -*-
#
import re
from collections import OrderedDict
from itertools import chain
import logging
import datetime
import uuid
from functools import wraps
import time
import ipaddress
import psutil


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


class Time:
    def __init__(self):
        self._timestamps = []
        self._msgs = []

    def begin(self):
        self._timestamps.append(time.time())

    def time(self, msg):
        self._timestamps.append(time.time())
        self._msgs.append(msg)

    def print(self):
        last, *timestamps = self._timestamps
        for timestamp, msg in zip(timestamps, self._msgs):
            logger.debug(f'TIME_IT: {msg} {timestamp-last}')
            last = timestamp
