# 测试通过 view 动态创建 serializer


class BaseSerializerMetaClass(type):

    def __new__(mcs, name, bases, attrs):
        attrs.update({'color': 'blank'})
        return super().__new__(mcs, name, bases, attrs)


class BaseSerializer(metaclass=BaseSerializerMetaClass):
    x_id = 'id_value'


class Serializer(BaseSerializer):

    x_name = 'name_value'
    x_hobby = {
        'music': 'chinese',
        'ball': 'basketball'
    }
    x_age = {
        'real': 19,
        'fake': 27
    }


# custom metaclass
class SerializerMetaClass(BaseSerializerMetaClass, type):

    @classmethod
    def _get_declared_x_attr_value(mcs, x_types, attr_name, attr_value):
        pass

    @classmethod
    def _get_declared_x_attrs(mcs, bases, attrs):
        x_types = attrs['view'].x_types

        bases_attrs = {}
        for base in bases:
            for k in dir(base):
                if not k.startswith('x_'):
                    continue
                v = getattr(base, k)
                if isinstance(v, str):
                    bases_attrs[k] = v
                    continue
                if isinstance(v, dict):
                    v = mcs._get_declared_x_attr_value( x_types, k, v)
                    bases_attrs[k] = v
        attrs.update(bases_attrs)
        return attrs

    def __new__(mcs, name, bases, attrs):
        attrs = mcs._get_declared_x_attrs(bases, attrs)
        return super().__new__(mcs, name, bases, attrs)


class View(object):
    x_types = ['x_age', 'fake']
    serializer_class = Serializer

    def get_serializer_class(self):
        return self.serializer_class

    def build_serializer_class(self):
        serializer_class = self.get_serializer_class()
        serializer_class = SerializerMetaClass(
            serializer_class.__name__, (serializer_class,), {'view': self}
        )
        return serializer_class


view = View()


serializer = view.build_serializer_class()
print('End!')

#
from rest_framework.serializers import SerializerMetaclass


data = {
    'meta': {
        'type': {
            'apply_asset': {
                'get': 'get',
                'post': 'post'
            }
        }
    }
}




def get_value(key_list, data_dict):
    if len(key_list) == 0:
        return data_dict
    for i, key in enumerate(key_list):
        _keys = key_list[i+1:]
        _data = data_dict.get(key)
        if _data is None:
            return data_dict
        if not isinstance(_data, dict):
            return _data
        return get_value(_keys, _data)



keys = ['meta', 'type', 'apply_asset', 'get']
value = get_value(keys, data)
print(value)

keys = ['meta', 'type', 'apply_asset', 'post']
value = get_value(keys, data)
print(value)

keys = ['meta', 'type', 'apply_asset', 'xxxxx']
value = get_value(keys, data)
print(value)

keys = ['meta', 'type', 'apply_asset', 'post', 'xxxxxxxx']
value = get_value(keys, data)
print(value)

