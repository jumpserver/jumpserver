from common.exceptions import JMSException
from tickets import const, serializers


__all__ = ['TicketMetaSerializerViewMixin']


class TicketMetaSerializerViewMixin:
    apply_asset_meta_serializer_classes = {
        'apply': serializers.TicketMetaApplyAssetApplySerializer,
        'approve': serializers.TicketMetaApplyAssetApproveSerializer,
    }
    apply_application_meta_serializer_classes = {
        'apply': serializers.TicketMetaApplyApplicationApplySerializer,
        'approve': serializers.TicketMetaApplyApplicationApproveSerializer,
    }
    login_confirm_meta_serializer_classes = {
        'apply': serializers.TicketMetaLoginConfirmApplySerializer,
    }
    meta_serializer_classes = {
        const.TicketTypeChoices.apply_asset.value: apply_asset_meta_serializer_classes,
        const.TicketTypeChoices.apply_application.value: apply_application_meta_serializer_classes,
        const.TicketTypeChoices.login_confirm.value: login_confirm_meta_serializer_classes,
    }

    def get_serializer_meta_field_class(self):
        tp = self.request.query_params.get('type')
        if not tp:
            return None
        tp_choices = const.TicketTypeChoices.types()
        if tp not in tp_choices:
            raise JMSException(
                'Invalid query parameter `type`, select from the following options: {}'
                ''.format(tp_choices)
            )
        meta_class = self.meta_serializer_classes.get(tp, {}).get(self.action)
        return meta_class

    def get_serializer_meta_field(self):
        if self.action not in ['apply', 'approve']:
            return None
        meta_class = self.get_serializer_meta_field_class()
        if not meta_class:
            return None
        return meta_class(required=True)

    def reset_view_action(self):
        if self.action not in ['metadata']:
            return
        view_action = self.request.query_params.get('action')
        if not view_action:
            raise JMSException('The `metadata` methods must carry parameter `action`')
        setattr(self, 'action', view_action)

    def get_serializer_class(self):
        self.reset_view_action()
        serializer_class = super().get_serializer_class()
        if getattr(self, 'swagger_fake_view', False):
            return serializer_class
        meta_field = self.get_serializer_meta_field()
        if not meta_field:
            return serializer_class
        serializer_class = type(
            meta_field.__class__.__name__, (serializer_class,), {'meta': meta_field}
        )
        return serializer_class
