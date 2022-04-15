import time

from channels_redis.core import RedisChannelLayer as _RedisChannelLayer

from common.utils.lock import DistributedLock
from common.utils.connection import get_redis_client
from common.utils import lazyproperty
from common.utils import get_logger

logger = get_logger(__file__)


class ComputeLock(DistributedLock):
    """
    需要重建缓存的时候加上该锁，避免重复计算
    """
    def __init__(self, key):
        name = f'compute:{key}'
        super().__init__(name=name)


class CacheFieldBase:
    field_type = str

    def __init__(self, queryset=None, compute_func_name=None):
        assert None in (queryset, compute_func_name), f'queryset and compute_func_name can only have one'
        self.compute_func_name = compute_func_name
        self.queryset = queryset


class CharField(CacheFieldBase):
    field_type = str


class IntegerField(CacheFieldBase):
    field_type = int


class CacheType(type):
    def __new__(cls, name, bases, attrs: dict):
        to_update = {}
        field_desc_mapper = {}

        for k, v in attrs.items():
            if isinstance(v, CacheFieldBase):
                desc = CacheValueDesc(k, v)
                to_update[k] = desc
                field_desc_mapper[k] = desc

        attrs.update(to_update)
        attrs['field_desc_mapper'] = field_desc_mapper
        return type.__new__(cls, name, bases, attrs)


class Cache(metaclass=CacheType):
    field_desc_mapper: dict
    timeout = None

    def __init__(self):
        self._data = None
        self.redis = get_redis_client()

    def __getitem__(self, item):
        return self.field_desc_mapper[item]

    def __contains__(self, item):
        return item in self.field_desc_mapper

    def get_field(self, name):
        return self.field_desc_mapper[name]

    @property
    def fields(self):
        return self.field_desc_mapper.values()

    @property
    def field_names(self):
        names = self.field_desc_mapper.keys()
        return names

    @lazyproperty
    def key_suffix(self):
        return self.get_key_suffix()

    @property
    def key_prefix(self):
        clz = self.__class__
        return f'cache.{clz.__module__}.{clz.__name__}'

    @property
    def key(self):
        return f'{self.key_prefix}.{self.key_suffix}'

    @property
    def data(self):
        if self._data is None:
            data = self.load_data_from_db()
            if not data:
                with ComputeLock(self.key):
                    data = self.load_data_from_db()
                    if not data:
                        # 缓存中没有数据时，去数据库获取
                        self.init_all_values()
        return self._data

    def to_internal_value(self, data: dict):
        internal_data = {}
        for k, v in data.items():
            field = k.decode()
            if field in self:
                value = self[field].to_internal_value(v.decode())
                internal_data[field] = value
            else:
                logger.warn(f'Cache got invalid field: '
                            f'key={self.key} '
                            f'invalid_field={field} '
                            f'valid_fields={self.field_names}')
        return internal_data

    def load_data_from_db(self) -> dict:
        data = self.redis.hgetall(self.key)
        logger.debug(f'Get data from cache: key={self.key} data={data}')
        if data:
            data = self.to_internal_value(data)
            self._data = data
        return data

    def save_data_to_db(self, data):
        logger.debug(f'Set data to cache: key={self.key} data={data}')
        self.redis.hset(self.key, mapping=data)
        self.load_data_from_db()

    def compute_values(self, *fields):
        field_objs = []
        for field in fields:
            field_objs.append(self[field])

        data = {
            field_obj.field_name: field_obj.compute_value(self)
            for field_obj in field_objs
        }
        return data

    def init_all_values(self):
        t_start = time.time()
        logger.debug(f'Start init cache: key={self.key}')
        data = self.compute_values(*self.field_names)
        self.save_data_to_db(data)
        logger.debug(f'End init cache: cost={time.time()-t_start} key={self.key}')
        return data

    def refresh(self, *fields):
        if not fields:
            # 没有指定 field 要刷新所有的值
            self.init_all_values()
            return

        data = self.load_data_from_db()
        if not data:
            # 缓存中没有数据，设置所有的值
            self.init_all_values()
            return

        refresh_values = self.compute_values(*fields)
        self.save_data_to_db(refresh_values)

    def get_key_suffix(self):
        raise NotImplementedError

    def reload(self):
        self._data = None

    def expire(self, *fields):
        self._data = None
        if not fields:
            self.redis.delete(self.key)
        else:
            self.redis.hdel(self.key, *fields)
            logger.debug(f'Expire cached fields: key={self.key} fields={fields}')


class CacheValueDesc:
    def __init__(self, field_name, field_type: CacheFieldBase):
        self.field_name = field_name
        self.field_type = field_type
        self._data = None

    def __repr__(self):
        clz = self.__class__
        return f'<{clz.__name__} {self.field_name} {self.field_type}>'

    def __get__(self, instance: Cache, owner):
        if instance is None:
            return self
        if self.field_name not in instance.data:
            instance.refresh(self.field_name)
        # 防止边界情况没有值，报错
        value = instance.data.get(self.field_name)
        return value

    def compute_value(self, instance: Cache):
        t_start = time.time()
        logger.debug(f'Start compute cache field: field={self.field_name} key={instance.key}')
        if self.field_type.queryset is not None:
            new_value = self.field_type.queryset.count()
        else:
            compute_func_name = self.field_type.compute_func_name
            if not compute_func_name:
                compute_func_name = f'compute_{self.field_name}'
            compute_func = getattr(instance, compute_func_name, None)
            assert compute_func is not None, \
                f'Define `{compute_func_name}` method in {instance.__class__}'
            new_value = compute_func()

        new_value = self.field_type.field_type(new_value)
        logger.debug(f'End compute cache field: cost={time.time()-t_start} field={self.field_name} value={new_value} key={instance.key}')
        return new_value

    def to_internal_value(self, value):
        return self.field_type.field_type(value)


class RedisChannelLayer(_RedisChannelLayer):
    async def _brpop_with_clean(self, index, channel, timeout):
        cleanup_script = """
            local backed_up = redis.call('ZRANGE', ARGV[2], 0, -1, 'WITHSCORES')
            for i = #backed_up, 1, -2 do
                redis.call('ZADD', ARGV[1], backed_up[i], backed_up[i - 1])
            end
            redis.call('DEL', ARGV[2])
        """
        backup_queue = self._backup_channel_name(channel)
        async with self.connection(index) as connection:
            # 部分云厂商的 Redis 此操作会报错(不支持，比如阿里云有限制)
            try:
                await connection.eval(cleanup_script, keys=[], args=[channel, backup_queue])
            except:
                pass
            result = await connection.bzpopmin(channel, timeout=timeout)

            if result is not None:
                _, member, timestamp = result
                await connection.zadd(backup_queue, float(timestamp), member)
            else:
                member = None
            return member
