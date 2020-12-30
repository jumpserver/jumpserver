from common.exceptions import JMSException
from tickets import const, serializers


__all__ = ['TicketJSONFieldsSerializerViewMixin']


class TicketJSONFieldsSerializerViewMixin:
    json_fields_category_mapping = {
        'meta': {
            'type': const.TicketTypeChoices.values,
        },
    }
    json_fields_serializer_classes = {
        'meta': {
            'type': {
                const.TicketTypeChoices.apply_asset.value: {
                    'open': {
                        'class': serializers.TicketMetaApplyAssetApplySerializer,
                        'attrs': {'required': True}
                    },
                    'approve': {
                        'class': serializers.TicketMetaApplyAssetApproveSerializer,
                        'attrs': {'required': True}
                    }
                },
                const.TicketTypeChoices.apply_application.value: {
                    'open': {
                        'class': serializers.TicketMetaApplyApplicationApplySerializer,
                        'attrs': {'required': True}
                    },
                    'approve': {
                        'class': serializers.TicketMetaApplyApplicationApproveSerializer,
                        'attrs': {'required': True}
                    }
                },
                const.TicketTypeChoices.login_confirm.value: {
                    'open': {
                        'class': serializers.TicketMetaLoginConfirmApplySerializer,
                        'attrs': {'required': True}
                    }
                }
            }
        }
    }
