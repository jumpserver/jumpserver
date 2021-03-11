from django.utils.translation import ugettext as _
from django.db.models.functions import Concat
from django.db.models import F, Value
from rest_framework import serializers
from common.drf.serializers import BulkModelSerializer
from ..models import LoginACL
from ..utils import is_ip_address, is_ip_network,  is_ip_segment
from .. import const


__all__ = ['LoginACLSerializer', 'LoginACLUserRelationSerializer']


def ip_group_child_validator(ip_group_child):
    is_valid = ip_group_child == '*' \
               or is_ip_address(ip_group_child) \
               or is_ip_network(ip_group_child) \
               or is_ip_segment(ip_group_child)
    if not is_valid:
        error = _('Ip address invalid: `{}`').format(ip_group_child)
        raise serializers.ValidationError(error)


class LoginACLSerializer(BulkModelSerializer):
    ip_group = serializers.ListField(
        default=['*'],
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator]),
        label=_('IP'),
        help_text=const.ip_group_help_text + _('Domain name support.')
    )
    users_amount = serializers.IntegerField(read_only=True, source='users.count')

    class Meta:
        model = LoginACL
        fields = [
            'id', 'name', 'priority', 'ip_group', 'users', 'users_amount', 'action', 'comment',
            'created_by', 'date_created', 'date_updated'
        ]


class LoginACLUserRelationSerializer(BulkModelSerializer):
    loginacl_display = serializers.ReadOnlyField(source='loginacl.name')
    user_display = serializers.ReadOnlyField()

    class Meta:
        model = LoginACL.users.through
        fields = [
            'id', 'loginacl', 'user', 'loginacl_display', 'user_display'
        ]

    @staticmethod
    def setup_eager_loading(queryset):
        queryset = queryset.prefetch_related('user').annotate(
            user_display=Concat(F('user__name'), Value('('), F('user__username'), Value(')')),
        )
        return queryset
