from django.shortcuts import get_object_or_404
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import AutomationTypes, GatherAccountDetailField
from accounts.models import GatherAccountsAutomation
from accounts.models import GatheredAccount
from accounts.serializers.account.account import AccountAssetSerializer as _AccountAssetSerializer
from accounts.serializers.account.base import BaseAccountSerializer
from common.const import ConfirmOrIgnore
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .base import BaseAutomationSerializer

__all__ = [
    'DiscoverAccountSerializer',
    'DiscoverAccountActionSerializer',
    'DiscoverAccountAutomationSerializer',
    'DiscoverAccountDetailsSerializer'
]


class DiscoverAccountAutomationSerializer(BaseAutomationSerializer):
    class Meta:
        model = GatherAccountsAutomation
        read_only_fields = BaseAutomationSerializer.Meta.read_only_fields
        fields = (BaseAutomationSerializer.Meta.fields
                  + ['is_sync_account', 'check_risk', 'recipients']
                  + read_only_fields)
        extra_kwargs = {
            'check_risk': {
                'help_text': _('Whether to check the risk of the gathered accounts.'),
            },
            **BaseAutomationSerializer.Meta.extra_kwargs
        }

    @property
    def model_type(self):
        return AutomationTypes.gather_accounts


class AccountAssetSerializer(_AccountAssetSerializer):
    class Meta(_AccountAssetSerializer.Meta):
        ref_name = "GatheredAccountAssetSerializer"
        fields = [f for f in _AccountAssetSerializer.Meta.fields if f != 'auto_config']


class DiscoverAccountSerializer(BulkOrgResourceModelSerializer):
    asset = AccountAssetSerializer(label=_('Asset'))

    class Meta(BaseAccountSerializer.Meta):
        model = GatheredAccount
        fields = [
            'id', 'asset', 'username',
            'date_last_login', 'address_last_login',
            'remote_present', 'present',
            'date_updated', 'status', 'detail'
        ]
        read_only_fields = fields

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('asset', 'asset__platform')
        return queryset


class DiscoverAccountActionSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), required=True)
    status = serializers.ChoiceField(choices=ConfirmOrIgnore.choices, default=ConfirmOrIgnore.pending, allow_blank=True)

    class Meta:
        fields = ['ids', 'status']


class DiscoverAccountDetailsSerializer(serializers.Serializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if not request:
            return

        params = request.query_params
        if params.get('format') == 'openapi':
            return

        pk = request.parser_context['kwargs'].get('pk')
        obj = get_object_or_404(GatheredAccount, pk=pk)
        details = obj.detail
        for key, value in details.items():
            field_dict = GatherAccountDetailField._member_map_
            label = field_dict[key].label if key in field_dict else key
            if isinstance(value, bool):
                self.fields[key] = serializers.BooleanField(label=label, read_only=True)
            else:
                self.fields[key] = serializers.CharField(label=label, read_only=True)
