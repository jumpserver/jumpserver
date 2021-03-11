from django.utils.translation import ugettext as _
from rest_framework import serializers
from common.drf.serializers import BulkModelSerializer
from orgs.utils import current_org
from ..models import LoginACL
from ..utils import is_ip_address, is_ip_network,  is_ip_segment
from .. import const


__all__ = ['LoginACLSerializer', ]


def ip_group_child_validator(ip_group_child):
    is_valid = ip_group_child == '*' \
               or is_ip_address(ip_group_child) \
               or is_ip_network(ip_group_child) \
               or is_ip_segment(ip_group_child)
    if not is_valid:
        error = _('IP address invalid: `{}`').format(ip_group_child)
        raise serializers.ValidationError(error)


class LoginACLSerializer(BulkModelSerializer):
    ip_group = serializers.ListField(
        default=['*'], label=_('IP'), help_text=const.ip_group_help_text,
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator])
    )
    user_display = serializers.ReadOnlyField(source='user.name', label=_('User'))
    action_display = serializers.ReadOnlyField(source='get_action_display', label=_('Action'))

    class Meta:
        model = LoginACL
        fields = [
            'id', 'name', 'priority', 'ip_group', 'user', 'user_display', 'action',
            'action_display', 'is_active', 'comment', 'created_by', 'date_created', 'date_updated'
        ]
        extra_kwargs = {
            'priority': {'default': 50},
            'is_active': {'default': True},
        }

    @staticmethod
    def validate_user(user):
        if user not in current_org.get_members():
            error = _('The user `{}` is not in the current organization: `{}`').format(
                user, current_org
            )
            raise serializers.ValidationError(error)
        return user
