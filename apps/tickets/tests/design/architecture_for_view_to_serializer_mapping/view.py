from tickets.tests.design.architecture_for_view_to_serializer_mapping.serializer import (
    IncludeDynamicMappingFieldSerializerMetaClass, TicketSerializer
)


#
# IncludeDynamicMappingFieldSerializerViewMixin
# ---------------------------------------------


class IncludeDynamicMappingFieldSerializerViewMixin:
    """
    动态创建 `view` 使用的 `serializer_class`,

    根据用户请求行为的不同, 构造出获取 `serializer_class` 中 `common.drf.fields.DynamicMappingField` 字段
    的映射规则, 并通过 `IncludeDynamicMappingFieldSerializerMetaClass` 元类，
    基于父类的 `serializer_class` 和 构造出的映射规则 `dynamic_mapping_fields_mapping_rule`
    创建出满足要求的新的 `serializer_class`

    * 重写 get_dynamic_mapping_fields_mapping_rule 方法:

    For example,

    def  get_dynamic_mapping_fields_mapping_rule(self):
        return {'meta': ['type', 'apply_asset', 'get']

    """

    def get_dynamic_mapping_fields_mapping_rule(self):
        """
        return:
        {
            'meta': ['type', 'apply_asset', 'get'],
            'meta2': 'category.login'
        }
        """
        print(self)
        return {
            'meta1': ['type', 'apply_asset', 'getX', 'asdf'],
            'meta2': 'category.login',
            'meta3': 'type.apply_asset.',
            'meta4': 'category.apply'
        }

    @staticmethod
    def _create_serializer_class(base, attrs):
        serializer_class = IncludeDynamicMappingFieldSerializerMetaClass(
            base.__name__, (base, ), attrs
        )
        return serializer_class

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()

        fields_mapping_rule = self.get_dynamic_mapping_fields_mapping_rule()
        if not fields_mapping_rule:
            return serializer_class

        attrs = {'dynamic_mapping_fields_mapping_rule': fields_mapping_rule}
        serializer_class = self._create_serializer_class(base=serializer_class, attrs=attrs)
        return serializer_class


#
# Test data
# ---------


class GenericViewSet(object):

    def get_serializer_class(self):
        return TicketSerializer


class TicketViewSet(IncludeDynamicMappingFieldSerializerViewMixin, GenericViewSet):
    pass


view = TicketViewSet()

_serializer_class = view.get_serializer_class()

_serializer = _serializer_class()

print(_serializer_class)
print(_serializer)
