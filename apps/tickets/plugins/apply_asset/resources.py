from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from assets.models import Asset, Node
from perms.serializers.permission import ActionChoicesField
from perms.utils.expire_soon_notice import sync_ticket_expire_soon_notice
from tickets.plugins.resources import RequestSerializer


class ResourceSerializer(RequestSerializer):
    apply_assets = serializers.ListField(child=serializers.UUIDField(), max_length=100, default=list,
                                        label=_('Assets'), style={'resource': 'asset'})
    apply_nodes = serializers.ListField(child=serializers.UUIDField(), max_length=100, default=list,
                                       label=_('Nodes'), style={'resource': 'node'})
    apply_accounts = serializers.ListField(child=serializers.CharField(max_length=128), allow_empty=False,
                                          max_length=100, label=_('Accounts'), style={'resource': 'account_selector'})
    apply_actions = ActionChoicesField(label=_('Actions'))
    apply_date_start = serializers.DateTimeField(label=_('Date start'))
    apply_date_expired = serializers.DateTimeField(label=_('Date expired'))
    apply_expire_soon_notice_minutes = serializers.IntegerField(min_value=1, allow_null=True, default=None,
                                                              label=_('Expiration-soon notice minutes'))

    def validate(self, attrs):
        org_id = self.context['org_id']
        for name, model in (('apply_assets', Asset), ('apply_nodes', Node)):
            ids = attrs[name]
            qs = model.objects.filter(pk__in=ids, org_id=org_id)
            if model == Asset:
                qs = qs.filter(is_active=True)
            if qs.count() != len(set(ids)):
                raise serializers.ValidationError({name: _('Resources must belong to the selected organization.')})
        if attrs['apply_nodes'] and 'assets.view_node' not in self.context['request'].user.get_all_permissions():
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied()
        if not (attrs['apply_assets'] or attrs['apply_nodes']):
            raise serializers.ValidationError({'apply_assets': _('Select at least one asset or node')})
        if attrs['apply_date_expired'] <= attrs['apply_date_start']:
            raise serializers.ValidationError({'apply_date_expired': _('The expiration date should be greater than the start date')})
        try:
            sync_ticket_expire_soon_notice(None, attrs)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs
