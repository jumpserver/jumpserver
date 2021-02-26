from ipaddress import ip_network
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from orgs.mixins.serializers import OrgResourceModelSerializerMixin
from .models import AssetACLPolicy


def is_cidr_ip(value):
    """
    References: https://en.wikipedia.org/wiki/Classless_Inter-Domain_Routing
    :param value:
    :return:
    """
    try:
        ip_network(value)
    except Exception as e:
        raise serializers.ValidationError(_("Invalid ip"))
    return value


class AssetACLPolicySerializer(OrgResourceModelSerializerMixin):
    ip = serializers.CharField(max_length=128, validators=[is_cidr_ip])
    port = serializers.IntegerField(max_value=65535, min_value=0)

    class Meta:
        model = AssetACLPolicy
        fields = [
            'id', 'name', 'user', 'ip', 'port', 'system_user', 'is_active',
            'reviewers',
        ]
