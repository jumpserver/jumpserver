import copy
from common.drf.fields import IgnoreSensitiveInfoReadOnlyJSONField
from tickets import const
from . import apply_asset, apply_application, login_confirm

__all__ = [
    'get_meta_field_dynamic_mapping_rules',
    'get_meta_field_mapping_rule_by_view',
]

#
# ticket type
# -----------


type_apply_asset = const.TicketTypeChoices.apply_asset.value
type_apply_application = const.TicketTypeChoices.apply_application.value
type_login_confirm = const.TicketTypeChoices.login_confirm.value

#
# ticket action
# -------------


actions = const.TicketActionChoices.values
action_open = const.TicketActionChoices.open.value
action_approve = const.TicketActionChoices.approve.value
action_reject = const.TicketActionChoices.reject.value
action_close = const.TicketActionChoices.close.value


#
# defines the dynamic mapping rules for the DynamicMappingField `meta`
# --------------------------------------------------------------------


__META_FIELD_DYNAMIC_MAPPING_RULES = {
    'default': IgnoreSensitiveInfoReadOnlyJSONField,
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


# Note:
# The dynamic mapping rules of `meta` field is obtained
# through call method `get_meta_field_dynamic_mapping_rules`

def get_meta_field_dynamic_mapping_rules():
    return copy.deepcopy(__META_FIELD_DYNAMIC_MAPPING_RULES)


#
# get `meta dynamic field` mapping rule by `view object`
# ------------------------------------------------------


def get_meta_field_mapping_rule_by_view(view):
    query_type = view.request.query_params.get('type')
    query_action = view.request.query_params.get('action')
    action = query_action if query_action else view.action
    mapping_rule = ['type', query_type, action]
    return mapping_rule
