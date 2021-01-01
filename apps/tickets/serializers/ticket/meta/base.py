import copy
from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from common.exceptions import JMSException
from tickets import const
from . import apply_asset, apply_application, login_confirm

__all__ = [
    'meta_dynamic_mapping_fields_mapping_rules',
    'get_meta_field_rule_by_view',
]


# ticket type
types = const.TicketTypeChoices.values
type_apply_asset = const.TicketTypeChoices.apply_asset.value
type_apply_application = const.TicketTypeChoices.apply_application.value
type_login_confirm = const.TicketTypeChoices.login_confirm.value

# ticket action
actions = const.TicketActionChoices.values
action_open = const.TicketActionChoices.open.value
action_approve = const.TicketActionChoices.approve.value
action_reject = const.TicketActionChoices.reject.value
action_close = const.TicketActionChoices.close.value


meta_dynamic_mapping_fields_mapping_rules = {
    'default': serializers.ReadOnlyField,
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


def get_meta_field_rule_by_view(view):
    mapping_rules = copy.deepcopy(meta_dynamic_mapping_fields_mapping_rules)
    request = view.request

    # type
    tp = request.query_params.get('type')
    if not tp:
        return ['default']
    if tp not in types:
        error = _('Query parameter `type` ({}) not in choices: {}'.format(tp, types))
        raise JMSException(error)
    if tp not in mapping_rules['type']:
        return ['default']

    # action
    action = view.action
    if action in ['metadata']:
        # options
        action = request.query_params.get('action')
        if not action:
            error = _('Please carry query parameter `action`')
            raise JMSException(error)
        if action not in actions:
            error = _('Query parameter `action` ({}) not in choices: {}'.format(action, actions))
            raise JMSException(error)
        if action not in mapping_rules['type'][tp]:
            return ['default']

    # display
    if action in ['list', 'retrieve']:
        return ['default']

    if not mapping_rules['type'][tp].get(action):
        return ['default']

    return ['type', tp, action]





