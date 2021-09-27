from django.utils.translation import ugettext as _
from rest_framework import serializers
from common.drf.serializers import BulkModelSerializer
from orgs.utils import current_org
from ..models import LoginACL
from common.utils.ip import is_ip_address, is_ip_network, is_ip_segment

__all__ = ['LoginACLSerializer', ]


def ip_group_child_validator(ip_group_child):
    is_valid = ip_group_child == '*' \
               or is_ip_address(ip_group_child) \
               or is_ip_network(ip_group_child) \
               or is_ip_segment(ip_group_child)
    if not is_valid:
        error = _('IP address invalid: `{}`').format(ip_group_child)
        raise serializers.ValidationError(error)


common_help_text = _('Format for comma-delimited string, with * indicating a match all. ')


class LoginACLUsersSerializer(serializers.Serializer):
    username_group = serializers.ListField(
        default=[], child=serializers.CharField(max_length=128), label=_('Username'),
        help_text=common_help_text
    )


class LoginACLSerializer(BulkModelSerializer):
    ip_group_help_text = _(
        'Format for comma-delimited string, with * indicating a match all. '
        'Such as: '
        '192.168.10.1, 192.168.1.0/24, 10.1.1.1-10.1.1.20, 2001:db8:2de::e13, 2001:db8:1a:1110::/64 '
    )

    ip_group = serializers.ListField(
        default=['*'], label=_('IP'), help_text=ip_group_help_text,
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator]))
    user_display = serializers.ReadOnlyField(source='user.name', label=_('Username'))
    reviewers_display = serializers.SerializerMethodField(label=_('Reviewers'))
    action_display = serializers.ReadOnlyField(source='get_action_display', label=_('Action'))
    reviewers_amount = serializers.IntegerField(read_only=True, source='reviewers.count')
    users = LoginACLUsersSerializer(required=False)

    class Meta:
        model = LoginACL
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'priority', 'ip_group', 'action', 'action_display',
            'is_active', 'user', 'user_display', 'users',
            'date_created', 'date_updated', 'reviewers_amount',
            'comment', 'created_by'
        ]
        fields_fk = ['user', 'user_display', ]
        fields_m2m = ['reviewers', 'reviewers_display']
        fields = fields_small + fields_fk + fields_m2m
        extra_kwargs = {
            'priority': {'default': 50},
            'is_active': {'default': True},
            "reviewers": {'allow_null': False, 'required': True},
        }

    def get_reviewers_display(self, obj):
        return ','.join([str(user) for user in obj.reviewers.all()])
