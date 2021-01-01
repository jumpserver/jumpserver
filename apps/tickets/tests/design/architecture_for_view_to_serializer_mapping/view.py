from tickets.tests.design.architecture_for_view_to_serializer_mapping.serializer import (
    IncludeDynamicMappingFieldSerializerMetaClass, TicketSerializer
)

# from rest_framework import viewsets


class IncludeDynamicMappingFieldSerializerViewMixin:

    def get_dynamic_mapping_fields_mapping_rule(self):
        """
        return:
        {
            'meta': ['type', 'apply_asset', 'getX'],
            'meta2': ['category', 'login']
        }
        """
        print(self)
        return {
            'meta1': ['type', 'apply_asset', 'getX'],
            'meta2': ['category', 'login']
        }

    @staticmethod
    def create_serializer_class(base, attrs):
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
        serializer_class = self.create_serializer_class(base=serializer_class, attrs=attrs)
        return serializer_class


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
