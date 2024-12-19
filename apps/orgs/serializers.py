from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from .models import Organization
from .utils import get_current_org


class ResourceStatisticsSerializer(serializers.Serializer):
    users_amount = serializers.IntegerField(required=False, label=_('Users amount'))
    groups_amount = serializers.IntegerField(required=False, label=_('User groups amount'))

    assets_amount = serializers.IntegerField(required=False, label=_('Assets amount'))
    nodes_amount = serializers.IntegerField(required=False, label=_('Nodes amount'))
    domains_amount = serializers.IntegerField(required=False, label=_('Domains amount'))
    gateways_amount = serializers.IntegerField(required=False, label=_('Gateways amount'))

    asset_perms_amount = serializers.IntegerField(required=False, label=_('Asset permissions amount'))


class OrgSerializer(ModelSerializer):
    resource_statistics = ResourceStatisticsSerializer(source='resource_statistics_cache', read_only=True)

    class Meta:
        model = Organization
        fields_mini = ['id', 'name']
        fields_small = fields_mini + [
            'resource_statistics',
            'is_default', 'is_root', 'internal',
            'date_created', 'created_by',
            'comment', 'created_by',
        ]

        fields_m2m = []
        fields = fields_small + fields_m2m
        read_only_fields = ['created_by', 'date_created']


class CurrentOrgSerializer(ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'name', 'is_default', 'is_root', 'is_system', 'comment']


class CurrentOrgDefault:
    requires_context = False

    def __call__(self, *args):
        return get_current_org()

    def __repr__(self):
        return '%s()' % self.__class__.__name__
