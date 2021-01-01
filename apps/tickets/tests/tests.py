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


def get_value(keys_dict, data_dict):

    def _get_value(_key_list, _data_dict):
        if len(_key_list) == 0:
            return _data_dict
        for i, key in enumerate(_key_list):
            _keys = _key_list[i+1:]
            __data_dict = _data_dict.get(key)
            if __data_dict is None:
                return _data_dict
            if not isinstance(__data_dict, dict):
                return __data_dict
            return _get_value(_keys, __data_dict)

    _values_dict = {}
    for field, keys in keys_dict.items():
        keys.insert(0, field)
        _values_dict[field] = _get_value(keys, data_dict)
    return _values_dict


keys_dict_list = {
    'meta': ['type', 'apply_asset', 'get']
}
values_dict = get_value(keys_dict_list, data)
print(values_dict)

keys_dict_list = {
    'meta': ['type', 'apply_asset', 'post']
}
values_dict = get_value(keys_dict_list, data)
print(values_dict)

keys_dict_list = {
    'meta': ['type', 'apply_asset', 'post', 'dog']
}
values_dict = get_value(keys_dict_list, data)
print(values_dict)

keys_dict_list = {
    'meta': ['type', 'apply_asset', 'dog']
}
values_dict = get_value(keys_dict_list, data)
print(values_dict)


#

class A:
    def __init__(self):
        self.a = 'A'


get_action_serializer = 'GETSerializer'
post_action_serializer = 'POSTSerializer'
apply_action_serializer = A()

apply_asset_tree_serializer = {
    'get': get_action_serializer,
    'post': post_action_serializer,
    'apply': apply_action_serializer
}

type_tree_serializer = {
    'apply_asset': apply_asset_tree_serializer,
}

meta_tree_serializer = {
    'type': type_tree_serializer,
}

json_fields_serializer_mapping = {
    'meta': meta_tree_serializer
}


def data_dict_to_tree(data_dict):
    import data_tree
    t = data_tree.Data_tree_node(arg_data=data_dict)
    return t


tree = data_dict_to_tree(json_fields_serializer_mapping)


def get_tree_node(t, path):
    return t.get(path, arg_default_value_to_return='Not Found')


node = get_tree_node(tree, 'meta.type.apply_asset.get')
print(node)

node = get_tree_node(tree, 'meta.type.apply_asset.post')
print(node)

node = get_tree_node(tree, 'meta.type.apply_asset.apply')
print(node)


node = get_tree_node(tree, 'meta.type.apply_asset.xxxx')
print(node)
