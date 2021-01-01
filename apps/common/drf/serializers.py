import copy
from rest_framework import serializers
from rest_framework.serializers import Serializer
from rest_framework.serializers import ModelSerializer
from rest_framework_bulk.serializers import BulkListSerializer

from common.mixins import BulkListSerializerMixin
from common.drf.fields import DynamicMappingField
from common.mixins.serializers import BulkSerializerMixin

__all__ = [
    'IncludeDynamicMappingFieldSerializerMetaClass',
    'EmptySerializer', 'BulkModelSerializer', 'AdaptedBulkListSerializer', 'CeleryTaskSerializer'
]


#
# IncludeDynamicMappingFieldSerializerMetaClass
# ---------------------------------------------

class IncludeDynamicMappingFieldSerializerMetaClass(serializers.SerializerMetaclass, type):
    """
    SerializerMetaClass: 动态创建包含 `common.drf.fields.DynamicMappingField` 字段的 `SerializerClass`

    * Process only fields of type `DynamicMappingField` in `_declared_fields`
    * 只处理 `_declared_fields` 中类型为 `DynamicMappingField` 的字段

    根据 `attrs['dynamic_mapping_fields_mapping_rule']` 中指定的 `fields_mapping_rule`,
    从 `DynamicMappingField` 中匹配出满足给定规则的字段, 并使用匹配到的字段替换自身的 `DynamicMappingField`

    * 注意: 如果未能根据给定的匹配规则获取到对应的字段，先获取与给定规则同级的 `default` 字段，
           如果仍未获取到，则再获取 `DynamicMappingField`中定义的最外层的 `default` 字段

    * 说明: 如果获取到的不是 `serializers.Field` 类型, 则返回 `DynamicMappingField()`

    For example, define attrs['dynamic_mapping_fields_mapping_rule']:

    mapping_rules = {
        'default': serializer.JSONField,
        'type': {
            'apply_asset': {
                'default': serializer.ChoiceField(),
                'get': serializer.CharField()
            }
        }
    }
    meta = DynamicMappingField(mapping_rules=mapping_rules)

    dynamic_mapping_fields_mapping_rule = {'meta': ['type', 'apply_asset', 'get'],}
    => Got `serializer.CharField()`
    * or *
    dynamic_mapping_fields_mapping_rule = {{'meta': 'type.apply_asset.get',}}
    => Got `serializer.CharField()`
    * or *
    dynamic_mapping_fields_mapping_rule = {{'meta': 'type.apply_asset.',}}
    => Got serializer.ChoiceField(),
    * or *
    dynamic_mapping_fields_mapping_rule = {{'meta': 'type.apply_asset.xxx',}}
    => Got `serializer.ChoiceField()`
    * or *
    dynamic_mapping_fields_mapping_rule = {{'meta': 'type.apply_asset.get.xxx',}}
    => Got `serializer.JSONField()`
    * or *
    dynamic_mapping_fields_mapping_rule = {{'meta': 'type.apply_asset',}}
    => Got `{'get': {}}`, type is not `serializers.Field`, So `meta` is `DynamicMappingField()`
    """

    @classmethod
    def get_dynamic_mapping_fields(mcs, bases, attrs):
        fields = {}

        fields_mapping_rules = attrs.get('dynamic_mapping_fields_mapping_rule')

        assert isinstance(fields_mapping_rules, dict), (
            '`dynamic_mapping_fields_mapping_rule` must be `dict` type , but get `{}`'
            ''.format(type(fields_mapping_rules))
        )

        fields_mapping_rules = copy.deepcopy(fields_mapping_rules)

        declared_fields = mcs._get_declared_fields(bases, attrs)

        for field_name, field_mapping_rule in fields_mapping_rules.items():

            assert isinstance(field_mapping_rule, (list, str)), (
                '`dynamic_mapping_fields_mapping_rule.field_mapping_rule` '
                '- can be either a list of keys, or a delimited string. '
                'Such as:  `["type", "apply_asset", "get"]` or `type.apply_asset.get` '
                'but, get type is `{}`, `{}`'
                ''.format(type(field_mapping_rule), field_mapping_rule)
            )

            if field_name not in declared_fields.keys():
                continue

            declared_field = declared_fields[field_name]
            if not isinstance(declared_field, DynamicMappingField):
                continue

            dynamic_field = declared_field

            mapping_tree = dynamic_field.mapping_tree.copy()

            def get_field(rule):
                return mapping_tree.get(arg_path=rule)

            if isinstance(field_mapping_rule, str):
                field_mapping_rule = field_mapping_rule.split('.')

            field_mapping_rule[-1] = field_mapping_rule[-1] or 'default'

            field = get_field(rule=field_mapping_rule)

            if not field:
                field_mapping_rule[-1] = 'default'
                field = get_field(rule=field_mapping_rule)

            if field is None:
                field_mapping_rule = ['default']
                field = get_field(rule=field_mapping_rule)

            if isinstance(field, type):
                field = field()

            if not isinstance(field, serializers.Field):
                continue

            fields[field_name] = field

        return fields

    def __new__(mcs, name, bases, attrs):
        dynamic_mapping_fields = mcs.get_dynamic_mapping_fields(bases, attrs)
        attrs.update(dynamic_mapping_fields)
        return super().__new__(mcs, name, bases, attrs)

#
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


