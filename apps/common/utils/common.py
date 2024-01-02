# -*- coding: utf-8 -*-
#
import datetime
import ipaddress
import logging
import os
import platform
import re
import socket
import time
import uuid
from collections import OrderedDict
from functools import wraps
from itertools import chain

import psutil
from django.conf import settings
from django.templatetags.static import static

from common.permissions import ServiceAccountSignaturePermission

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
    if '/' in name:
        name = os.path.basename(name).replace('.py', '')
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
        ('M', rate ** 2),
        ('MB', rate ** 2),
        ('G', rate ** 3),
        ('GB', rate ** 3),
        ('T', rate ** 4),
        ('TB', rate ** 4),
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
            if rate > std_size / rate_ >= 1 or unit == "T":
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
        return all([is_uuid(x) for x in seq])
    return False


def get_request_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')
    if x_forwarded_for and x_forwarded_for[0]:
        login_ip = x_forwarded_for[0]
        return login_ip

    login_ip = request.META.get('REMOTE_ADDR', '')
    return login_ip


def get_request_ip_or_data(request):
    ip = ''

    if hasattr(request, 'data') and isinstance(request.data, dict) and request.data.get('remote_addr', ''):
        permission = ServiceAccountSignaturePermission()
        if permission.has_permission(request, None):
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


logger = get_logger(__name__)


def timeit(func):
    def wrapper(*args, **kwargs):
        name = func
        for attr in ('__qualname__', '__name__'):
            if hasattr(func, attr):
                name = getattr(func, attr)
                break

        logger.debug("Start call: {}".format(name))
        now = time.time()
        result = func(*args, **kwargs)
        using = (time.time() - now) * 1000
        msg = "Ends  call: {}, using: {:.1f}ms".format(name, using)
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


def get_disk_usage(path):
    return psutil.disk_usage(path=path).percent


def get_cpu_load():
    cpu_load_1, cpu_load_5, cpu_load_15 = psutil.getloadavg()
    cpu_count = psutil.cpu_count()
    single_cpu_load_1 = cpu_load_1 / cpu_count
    single_cpu_load_1 = '%.2f' % single_cpu_load_1
    return float(single_cpu_load_1)


def get_docker_mem_usage_if_limit():
    try:
        with open('/sys/fs/cgroup/memory/memory.limit_in_bytes') as f:
            limit_in_bytes = int(f.readline())
            total = psutil.virtual_memory().total
            if limit_in_bytes >= total:
                raise ValueError('Not limit')

        with open('/sys/fs/cgroup/memory/memory.usage_in_bytes') as f:
            usage_in_bytes = int(f.readline())

        with open('/sys/fs/cgroup/memory/memory.stat') as f:
            inactive_file = 0
            for line in f:
                if line.startswith('total_inactive_file'):
                    name, inactive_file = line.split()
                    break

                if line.startswith('inactive_file'):
                    name, inactive_file = line.split()
                    continue

            inactive_file = int(inactive_file)
        return ((usage_in_bytes - inactive_file) / limit_in_bytes) * 100

    except Exception as e:
        return None


def get_memory_usage():
    usage = get_docker_mem_usage_if_limit()
    if usage is not None:
        return usage
    return psutil.virtual_memory().percent


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
            logger.debug(f'TIME_IT: {msg} {timestamp - last}')
            last = timestamp


def bulk_get(d, keys, default=None):
    values = []
    for key in keys:
        values.append(d.get(key, default))
    return values


def unique(objects, key=None):
    seen = OrderedDict()

    if key is None:
        key = lambda item: item

    for obj in objects:
        v = key(obj)
        if v not in seen:
            seen[v] = obj
    return list(seen.values())


def get_file_by_arch(dir, filename):
    platform_name = platform.system()
    arch = platform.machine()

    file_path = os.path.join(
        settings.BASE_DIR, dir, platform_name, arch, filename
    )
    return file_path


def pretty_string(data, max_length=128, ellipsis_str='...'):
    """
    params:
       data: abcdefgh
       max_length: 7
       ellipsis_str: ...
   return:
       ab...gh
    """
    data = str(data)
    if len(data) < max_length:
        return data
    remain_length = max_length - len(ellipsis_str)
    half = remain_length // 2
    if half <= 1:
        return data[:max_length]
    start = data[:half]
    end = data[-half:]
    data = f'{start}{ellipsis_str}{end}'
    return data


def group_by_count(it, count):
    return [it[i:i + count] for i in range(0, len(it), count)]


def test_ip_connectivity(host, port, timeout=0.5):
    """
    timeout: seconds
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    result = sock.connect_ex((host, int(port)))
    sock.close()
    if result == 0:
        connectivity = True
    else:
        connectivity = False
    return connectivity


def static_or_direct(logo_path):
    if logo_path.startswith('img/'):
        return static(logo_path)
    else:
        return logo_path


def make_dirs(name, mode=0o755, exist_ok=False):
    """ 默认权限设置为 0o755 """
    return os.makedirs(name, mode=mode, exist_ok=exist_ok)


def distinct(seq, key=None):
    if key is None:
        # 如果未提供关键字参数，则默认使用元素本身作为比较键
        key = lambda x: x
    seen = set()
    result = []
    for item in seq:
        k = key(item)
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result
