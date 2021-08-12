from tickets import const
from .ticket_type import (
    apply_asset, apply_application, login_confirm,
    login_asset_confirm, command_confirm
)

__all__ = [
    'type_serializer_classes_mapping',
]

# ticket action
# -------------

action_open = const.TicketAction.open.value
action_approve = const.TicketAction.approve.value


# defines `meta` field dynamic mapping serializers
# ------------------------------------------------

type_serializer_classes_mapping = {
    const.TicketType.apply_asset.value: {
        'default': apply_asset.ApplySerializer
    },
    const.TicketType.apply_application.value: {
        'default': apply_application.ApplySerializer
    },
    const.TicketType.login_confirm.value: {
        'default': login_confirm.LoginConfirmSerializer,
        action_open: login_confirm.ApplySerializer,
        action_approve: login_confirm.LoginConfirmSerializer(read_only=True),
    },
    const.TicketType.login_asset_confirm.value: {
        'default': login_asset_confirm.LoginAssetConfirmSerializer,
        action_open: login_asset_confirm.ApplySerializer,
        action_approve: login_asset_confirm.LoginAssetConfirmSerializer(read_only=True),
    },
    const.TicketType.command_confirm.value: {
        'default': command_confirm.CommandConfirmSerializer,
        action_open: command_confirm.ApplySerializer,
        action_approve: command_confirm.CommandConfirmSerializer(read_only=True)
    }
}
