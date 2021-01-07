from tickets import const
from .ticket_type import apply_asset, apply_application, login_confirm

__all__ = [
    'type_serializer_classes_mapping',
]

# ticket action
# -------------

action_open = const.TicketActionChoices.open.value
action_approve = const.TicketActionChoices.approve.value


# defines `meta` field dynamic mapping serializers
# ------------------------------------------------

type_serializer_classes_mapping = {
    const.TicketTypeChoices.apply_asset.value: {
        'any': apply_asset.ApplyAssetSerializer,
        action_open: apply_asset.ApplySerializer,
        action_approve: apply_asset.ApproveSerializer,
    },
    const.TicketTypeChoices.apply_application.value: {
        'any': apply_application.ApplyApplicationSerializer,
        action_open: apply_application.ApplySerializer,
        action_approve: apply_application.ApproveSerializer,
    },
    const.TicketTypeChoices.login_confirm.value: {
        'any': login_confirm.LoginConfirmSerializer,
        action_open: login_confirm.ApplySerializer,
    }
}
