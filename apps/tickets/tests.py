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
    def _get_declared_x_attrs(mcs, bases, attrs):
        view_x_types = getattr(attrs['view'], 'x_types')

        bases_attrs = {}
        for base in bases:
            for k in dir(base):
                if not k.startswith('x_'):
                    continue
                v = getattr(base, k)
                if isinstance(v, str):
                    bases_attrs[k] = v
                elif isinstance(v, dict):
                    if not view_x_types:
                        bases_attrs.update(v)
                        continue
                    if k not in view_x_types.keys():
                        bases_attrs.update(v)
                        continue
                    v = v[view_x_types[k]]
                    bases_attrs[k] = v
        attrs.update(bases_attrs)
        return attrs

    def __new__(mcs, name, bases, attrs):
        attrs = mcs._get_declared_x_attrs(bases, attrs)
        return super().__new__(mcs, name, bases, attrs)


class View(object):
    x_types = {
        'x_age': 'real'
    }
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


