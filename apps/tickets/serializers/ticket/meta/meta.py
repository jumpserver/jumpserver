from tickets import const
from .ticket_type import apply_asset, apply_application, login_confirm

__all__ = [
    'meta_field_dynamic_mapping_serializers',
]

# ticket type
# -----------


type_apply_asset = const.TicketTypeChoices.apply_asset.value
type_apply_application = const.TicketTypeChoices.apply_application.value
type_login_confirm = const.TicketTypeChoices.login_confirm.value

# ticket action
# -------------


actions = const.TicketActionChoices.values
action_open = const.TicketActionChoices.open.value
action_approve = const.TicketActionChoices.approve.value
action_reject = const.TicketActionChoices.reject.value
action_close = const.TicketActionChoices.close.value


# defines `meta` field dynamic mapping serializers
# ------------------------------------------------


meta_field_dynamic_mapping_serializers = {
    'type': {
        type_apply_asset: {
            action_open: apply_asset.ApplySerializer,
            action_approve: apply_asset.ApproveSerializer,
        },
        type_apply_application: {
            action_open: apply_application.ApplySerializer,
            action_approve: apply_application.ApproveSerializer,
        },
        type_login_confirm: {
            action_open: login_confirm.ApplySerializer,
        }
    }
}


