"""Shared resource validation without reading credential-bearing fields."""
from rest_framework import serializers
from django.utils.translation import gettext_lazy as _


class RequestSerializer(serializers.Serializer):
    def to_internal_value(self, data):
        if isinstance(data, dict) and data.keys() - self.fields.keys():
            raise serializers.ValidationError({key: 'Unknown request parameter.' for key in data.keys() - self.fields.keys()})
        return super().to_internal_value(data)


class AssetAccountRequestSerializer(RequestSerializer):
    asset = serializers.UUIDField(label=_('Asset'), style={'resource': 'asset'})
    accounts = serializers.ListField(child=serializers.CharField(max_length=128), allow_empty=False,
                                    max_length=100, label=_('Accounts'))

    def validate_asset(self, value):
        from assets.models import Asset
        from tickets.const import TicketApplyAssetScope
        from perms.utils import AssetPermissionPermAssetUtil
        from perms.utils.permission import AssetPermissionUtil
        from orgs.utils import tmp_to_org
        with tmp_to_org(self.context['org_id']):
            assets = Asset.objects.all()
            if TicketApplyAssetScope.is_permed() or TicketApplyAssetScope.is_permed_valid():
                permissions = AssetPermissionUtil().get_permissions_for_user(
                    self.context['request'].user, flat=True, with_expired=TicketApplyAssetScope.is_permed(),
                )
                assets = AssetPermissionPermAssetUtil(permissions).get_all_assets()
            if not assets.filter(pk=value, org_id=self.context['org_id']).exists():
                raise serializers.ValidationError('Select an asset available for application in this organization.')
        return value

    def validate(self, attrs):
        from accounts.models import Account
        from orgs.utils import tmp_to_org
        names = list(dict.fromkeys(attrs['accounts']))
        with tmp_to_org(self.context['org_id']):
            existing = set(Account.objects.filter(asset_id=attrs['asset'], asset__org_id=self.context['org_id'],
                                                 username__in=names).values_list('username', flat=True))
        if set(names) != existing:
            raise serializers.ValidationError({'accounts': 'Select existing accounts on the requested asset.'})
        attrs['accounts'] = names
        return attrs


def account_context(ticket):
    from accounts.models import Account
    from assets.models import Asset
    from tickets.workflow.context import snapshot_assets
    from tickets.workflow.errors import WorkflowConfigurationError
    request = dict(ticket.request_data)
    asset = Asset.objects.filter(pk=request['asset'], org_id=ticket.org_id).first()
    if not asset:
        raise WorkflowConfigurationError('The requested asset no longer exists.')
    accounts = list(Account.objects.filter(asset=asset, username__in=request['accounts']).values(
        'id', 'username', 'secret_type'))
    if {account['username'] for account in accounts} != set(request['accounts']):
        raise WorkflowConfigurationError('A requested account no longer exists.')
    for account in accounts:
        account.update(id=str(account['id']), asset_id=str(asset.pk))
    return {'request': request, 'assets': snapshot_assets([asset], ticket.org_id), 'accounts': accounts}


def validate_snapshot_assets(instance):
    from assets.models import Asset
    from tickets.workflow.errors import WorkflowConfigurationError
    ids = [asset['id'] for asset in instance.context['assets']]
    if Asset.objects.filter(pk__in=ids, org_id=instance.org_id).count() != len(ids):
        raise WorkflowConfigurationError('The requested asset was deleted or moved.')
