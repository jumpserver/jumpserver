import copy
from rest_framework import serializers
from rest_framework.serializers import Serializer
from rest_framework import serializers as s
from rest_framework.serializers import ModelSerializer
from rest_framework_bulk.serializers import BulkListSerializer

from django.utils.functional import cached_property

from jumpserver.conf import Config
from common.mixins import BulkListSerializerMixin
from common.mixins.serializers import BulkSerializerMixin

__all__ = [
    'MethodSerializer',
    'EmptySerializer', 'BulkModelSerializer', 'AdaptedBulkListSerializer', 'CeleryTaskSerializer'
]


# MethodSerializer
# ----------------


class MethodSerializer(serializers.Serializer):

    def __init__(self, method_name=None, **kwargs):
        self.method_name = method_name
        super().__init__(**kwargs)

    class Meta:
        # 生成swagger时使用
        ref_name = None

    def bind(self, field_name, parent):
        if self.method_name is None:
            method_name = 'get_{field_name}_serializer'.format(field_name=field_name)
            self.method_name = method_name

        super().bind(field_name, parent)

    @cached_property
    def serializer(self) -> serializers.Serializer:
        method = getattr(self.parent, self.method_name)
        _serializer = method()
        # 设置serializer的parent值，否则在serializer实例中获取parent会出现断层
        setattr(_serializer, 'parent', self.parent)
        return _serializer

    @cached_property
    def fields(self):
        """
        重写此方法因为在 BindingDict 中要设置每一个 field 的 parent 为 `serializer`,
        这样在调用 field.parent 时, 才会达到预期的结果，
        比如: serializers.SerializerMethodField
        """
        return self.serializer.fields

    def run_validation(self, data=serializers.empty):
        return self.serializer.run_validation(data)

    def to_representation(self, instance):
        return self.serializer.to_representation(instance)

    def get_initial(self):
        return self.serializer.get_initial()


# Other Serializer
# ----------------


class EmptySerializer(Serializer):
    pass


class BulkModelSerializer(BulkSerializerMixin, ModelSerializer):
    pass


class AdaptedBulkListSerializer(BulkListSerializerMixin, BulkListSerializer):
    pass


class CeleryTaskSerializer(serializers.Serializer):
    task = serializers.CharField(read_only=True)


class DataSerializerGenerator:
    type_field_mapper = {
        'str': s.CharField,
        'int': s.IntegerField,
        'float': s.FloatField,
        'list': s.ListSerializer,
        'dict': s.DictField,
        'bool': s.BooleanField,
    }

    @classmethod
    def generate_field(cls, field_data):
        """
        :param field_data: {'type': 'str', **kwargs }
        :return:
        """
        tp = field_data['type']
        if field_data.get('hidden'):
            serializer_field_cls = s.HiddenField
        elif field_data.get('choices'):
            serializer_field_cls = s.ChoiceField
        elif tp == 'str':
            field_data.setdefault('max_length', 1024)
            serializer_field_cls = s.URLField if field_data.get('url') else s.CharField
        else:
            serializer_field_cls = cls.type_field_mapper[tp]

        valid_data = {
            k: v for k, v in field_data.items()
            if k not in ['type', 'hidden', 'url', 'default']
        }

        field = serializer_field_cls(**valid_data)
        return field

    @classmethod
    def generate_serializer_class(cls, name):
        fields_data = {}
        for field in Config.fieldsets[name]['fields']:
            fields_data[field] = cls.generate_field(Config.fields[field])
        return type('{0}SettingSerializer'.format(name), (Serializer,), fields_data)
