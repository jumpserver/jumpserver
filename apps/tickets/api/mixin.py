from .. import const, serializers
from common.exceptions import JMSException


class TicketMetaSerializerViewMixin:

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        if getattr(self, 'swagger_fake_view', False):
            return serializer_class

        ticket_type = self.request.query_params.get('type')
        ticket_type_options = const.TicketTypeChoices.types()

        if ticket_type and ticket_type not in ticket_type_options:
            raise JMSException(
                'Invalid query parameter `type`, select from the following options: {}'
                ''.format(ticket_type_options)
            )

        if ticket_type == const.TicketTypeChoices.apply_asset.value:
            meta_class = serializers.TicketApplyAssetSerializer
            meta_class_name = meta_class.__name__
        else:
            meta_class = serializers.TicketNoMetaSerializer
            meta_class_name = meta_class.__name__
        cls = type(meta_class_name, (serializer_class,), {'meta': meta_class(required=False)})
        return cls
