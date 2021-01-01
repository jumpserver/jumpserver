from tickets.tests.design.architecture_for_view_to_serializer_mapping.serializer import (
    TreeSerializerMetaClass, TicketSerializer
)


class TicketViewSet(object):

    def get_json_fields_mapping(self):
        print(self)
        json_fields_mapping = {
            'meta': ['type', 'apply_asset', 'get'],
            'meta2': ['category', 'login'],
        }
        return json_fields_mapping

    def get_serializer_class(self):
        print(self)
        return TicketSerializer

    def build_serializer_class(self):
        serializer_class = self.get_serializer_class()
        json_fields_mapping = self.get_json_fields_mapping()
        serializer_class = TreeSerializerMetaClass(
            serializer_class.__name__, (serializer_class,),
            {'json_fields_mapping': json_fields_mapping}
        )
        return serializer_class



view = TicketViewSet()

serializer_class = view.build_serializer_class()

serializer = serializer_class()

print(serializer_class)
print(serializer)
