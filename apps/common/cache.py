import json
from django.core.cache import cache

from common.utils.lock import DistributedLock
from common.utils import lazyproperty
from common.utils import get_logger

logger = get_logger(__file__)


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


class CacheBase(type):
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


class Cache(metaclass=CacheBase):
    field_desc_mapper: dict
    timeout = None

    def __init__(self):
        self._data = None

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
            data = self.get_data()
            if data is None:
                # 缓存中没有数据时，去数据库获取
                self.compute_and_set_all_data()
        return self._data

    def get_data(self) -> dict:
        data = cache.get(self.key)
        logger.debug(f'Get data from cache: key={self.key} data={data}')
        if data is not None:
            data = json.loads(data)
            self._data = data
        return data

    def set_data(self, data):
        self._data = data
        to_json = json.dumps(data)
        logger.info(f'Set data to cache: key={self.key} data={to_json} timeout={self.timeout}')
        cache.set(self.key, to_json, timeout=self.timeout)

    def compute_data(self, *fields):
        field_descs = []
        if not fields:
            field_descs = self.field_desc_mapper.values()
        else:
            for field in fields:
                assert field in self.field_desc_mapper, f'{field} is not a valid field'
                field_descs.append(self.field_desc_mapper[field])
        data = {
            field_desc.field_name: field_desc.compute_value(self)
            for field_desc in field_descs
        }
        return data

    def compute_and_set_all_data(self, computed_data: dict = None):
        """
        TODO 怎样防止并发更新全部数据，浪费数据库资源
        """
        uncomputed_keys = ()
        if computed_data:
            computed_keys = computed_data.keys()
            all_keys = self.field_desc_mapper.keys()
            uncomputed_keys = all_keys - computed_keys
        else:
            computed_data = {}
        data = self.compute_data(*uncomputed_keys)
        data.update(computed_data)
        self.set_data(data)
        return data

    def refresh_part_data_with_lock(self, refresh_data):
        with DistributedLock(name=f'{self.key}.refresh'):
            data = self.get_data()
            if data is not None:
                data.update(refresh_data)
                self.set_data(data)
                return data

    def expire_fields_with_lock(self, *fields):
        with DistributedLock(name=f'{self.key}.refresh'):
            data = self.get_data()
            if data is not None:
                logger.info(f'Expire cached fields: key={self.key} fields={fields}')
                for f in fields:
                    data.pop(f)
                self.set_data(data)
                return data

    def refresh(self, *fields):
        if not fields:
            # 没有指定 field 要刷新所有的值
            self.compute_and_set_all_data()
            return

        data = self.get_data()
        if data is None:
            # 缓存中没有数据，设置所有的值
            self.compute_and_set_all_data()
            return

        refresh_data = self.compute_data(*fields)
        if not self.refresh_part_data_with_lock(refresh_data):
            # 刷新部分失败，缓存中没有数据，更新所有的值
            self.compute_and_set_all_data(refresh_data)
            return

    def get_key_suffix(self):
        raise NotImplementedError

    def reload(self):
        self._data = None

    def expire(self, *fields):
        if not fields:
            self._data = None
            logger.info(f'Delete cached key: key={self.key}')
            cache.delete(self.key)
        else:
            self.expire_fields_with_lock(*fields)


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
        logger.info(f'Compute cache field value: key={instance.key} field={self.field_name} value={new_value}')
        return new_value
