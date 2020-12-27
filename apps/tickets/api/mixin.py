from .. import const, serializers
from common.exceptions import JMSException


class TicketMetaSerializerViewMixin:
    apply_asset_meta_serializer_classes = {
        'default': serializers.TicketMetaApplyAssetSerializer,
        'display': serializers.TicketMetaApplyAssetSerializer,
        'apply': serializers.TicketMetaApplyAssetApplySerializer,
        'approve': serializers.TicketMetaApplyAssetApproveSerializer,
        'reject': serializers.TicketNoMetaSerializer,
        'close': serializers.TicketNoMetaSerializer,
    }
    login_confirm_meta_serializer_classes = {
        'default': serializers.TicketMetaLoginConfirmSerializer,
        'display': serializers.TicketMetaLoginConfirmSerializer,
        'apply': serializers.TicketMetaLoginConfirmSerializer,
        'approve': serializers.TicketNoMetaSerializer,
        'reject': serializers.TicketNoMetaSerializer,
        'close': serializers.TicketNoMetaSerializer,
    }
    meta_serializer_classes = {
        const.TicketTypeChoices.login_confirm.value: login_confirm_meta_serializer_classes,
        const.TicketTypeChoices.apply_asset.value: apply_asset_meta_serializer_classes,
    }

    def get_meta_class(self):
        default_meta_class = serializers.TicketNoMetaSerializer

        ticket_type = self.request.query_params.get('type')
        if not ticket_type:
            return default_meta_class

        ticket_type_choices = const.TicketTypeChoices.types()
        if ticket_type not in ticket_type_choices:
            raise JMSException(
                'Invalid query parameter `type`, select from the following options: {}'
                ''.format(ticket_type_choices)
            )

        type_meta_classes = self.meta_serializer_classes.get(ticket_type, {})
        meta_class = type_meta_classes.get(self.action, type_meta_classes['default'])
        return meta_class

    def get_serializer_class(self):
        serializer_class = super().get_serializer_class()
        if getattr(self, 'swagger_fake_view', False):
            return serializer_class
        meta_class = self.get_meta_class()
        if 'meta' in serializer_class().fields:
            params = {'meta': meta_class(required=False)}
        else:
            params = {}
        cls = type(meta_class.__name__, (serializer_class,), params)
        return cls
