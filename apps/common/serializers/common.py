import logging

from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from drf_writable_nested.serializers import WritableNestedModelSerializer as NestedModelSerializer
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer
from rest_framework.serializers import Serializer
from rest_framework_bulk.serializers import BulkListSerializer

from .mixin import BulkListSerializerMixin, BulkSerializerMixin

__all__ = [
    'MethodSerializer', 'EmptySerializer', 'BulkModelSerializer',
    'AdaptedBulkListSerializer', 'CeleryTaskExecutionSerializer',
    'WritableNestedModelSerializer', 'GroupedChoiceSerializer',
    'FileSerializer', 'DictSerializer'
]


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
        try:
            _serializer = method()
        except Exception as e:
            logging.error(e, exc_info=True)
            raise e
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


class EmptySerializer(Serializer):
    pass


class BulkModelSerializer(BulkSerializerMixin, ModelSerializer):
    pass


class AdaptedBulkListSerializer(BulkListSerializerMixin, BulkListSerializer):
    pass


class CeleryTaskExecutionSerializer(serializers.Serializer):
    task = serializers.CharField(read_only=True)


class ChoiceSerializer(serializers.Serializer):
    label = serializers.CharField(label=_("Label"))
    value = serializers.CharField(label=_("Value"))


class GroupedChoiceSerializer(ChoiceSerializer):
    children = ChoiceSerializer(many=True, label=_("Children"))


class WritableNestedModelSerializer(NestedModelSerializer):
    pass


class FileSerializer(serializers.Serializer):
    file = serializers.FileField(label=_("File"))


class DictSerializer(serializers.Serializer):

    def to_representation(self, instance):
        # 返回一个包含所有提交字段的 Python 字典
        return instance

    def to_internal_value(self, data):
        # 确保从请求中得到的输入是 Python 字典
        if isinstance(data, dict):
            return data
        else:
            raise serializers.ValidationError("无法转换为dict类型")
