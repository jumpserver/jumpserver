from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from ..models import Safe


__all__ = ['SafeSerializer']


class SafeSerializer(BulkOrgResourceModelSerializer):
    role_binding_amount = serializers.IntegerField(
        source='saferolebinding_set.count', read_only=True, label=_('Role binding amount')
    )
    accounts_amount = serializers.IntegerField(
        source='account_set.count', read_only=True, label=_('Accounts amount')
    )

    class Meta:
        model = Safe
        fields = [
            'id', 'name', 'accounts_amount', 'role_binding_amount', 'comment', 'date_created',
            'date_updated', 'created_by',
        ]
