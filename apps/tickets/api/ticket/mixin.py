from tickets import const, serializers


__all__ = ['TicketJSONFieldsModelSerializerViewMixin']


class TicketJSONFieldsModelSerializerViewMixin:
    json_fields_category_mapping = {
        'meta': {
            'type': const.TicketTypeChoices.values,
        },
    }
    json_fields_serializer_classes = {
        'meta': {
            'type': {
                const.TicketTypeChoices.apply_asset.value: {
                    'default': serializers.TicketMetaApplyAssetSerializer,
                    'open': serializers.TicketMetaApplyAssetApplySerializer,
                    'approve': serializers.TicketMetaApplyAssetApproveSerializer
                },
                const.TicketTypeChoices.apply_application.value: {
                    'default': serializers.TicketMetaApplyApplicationSerializer,
                    'open': serializers.TicketMetaApplyApplicationApplySerializer,
                    'approve':  serializers.TicketMetaApplyApplicationApproveSerializer,
                },
                const.TicketTypeChoices.login_confirm.value: {
                    'default': serializers.TicketMetaLoginConfirmSerializer,
                    'open': serializers.TicketMetaLoginConfirmApplySerializer
                }
            }
        }
    }
