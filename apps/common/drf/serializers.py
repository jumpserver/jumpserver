import copy
from rest_framework import serializers
from rest_framework.serializers import Serializer
from rest_framework.serializers import ModelSerializer
from rest_framework_bulk.serializers import BulkListSerializer

from common.mixins import BulkListSerializerMixin
from django.utils.functional import cached_property
from rest_framework.utils.serializer_helpers import BindingDict
from common.mixins.serializers import BulkSerializerMixin
from common.drf.fields import EncryptedField

__all__ = [
    'MethodSerializer',
    'EmptySerializer', 'BulkModelSerializer', 'AdaptedBulkListSerializer', 'CeleryTaskSerializer',
    'SecretReadableMixin'
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


class SecretReadableMixin(serializers.Serializer):
    """ 加密字段 (EncryptedField) 可读性 """

    def __init__(self, *args, **kwargs):
        super(SecretReadableMixin, self).__init__(*args, **kwargs)
        if not hasattr(self, 'Meta') or not hasattr(self.Meta, 'extra_kwargs'):
            return
        extra_kwargs = self.Meta.extra_kwargs
        for field_name, serializer_field in self.fields.items():
            if not isinstance(serializer_field, EncryptedField):
                continue
            if field_name not in extra_kwargs:
                continue
            field_extra_kwargs = extra_kwargs[field_name]
            if 'write_only' not in field_extra_kwargs:
                continue
            serializer_field.write_only = field_extra_kwargs['write_only']
