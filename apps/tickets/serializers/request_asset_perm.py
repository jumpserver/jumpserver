from rest_framework import serializers
from django.utils.translation import ugettext_lazy as _

from orgs.utils import current_org
from assets.models import SystemUser, Asset
from ..models import Ticket


class RequestAssetPermTicketSerializer(serializers.ModelSerializer):
    ips = serializers.ListField(child=serializers.IPAddressField(), source='meta.ips',
                                default=list, label=_('IP group'))
    hostname = serializers.CharField(max_length=256, source='meta.hostname', default=None,
                                      allow_blank=True, label=_('Hostname'))
    date_start = serializers.DateTimeField(source='meta.date_start', allow_null=True,
                                           required=False, label=_('Date start'))
    date_expired = serializers.DateTimeField(source='meta.date_expired', allow_null=True,
                                             required=False, label=_('Date expired'))
    confirmed_assets = serializers.ListField(child=serializers.UUIDField(),
                                             source='meta.confirmed_assets',
                                             default=list, required=False,
                                             label=_('Confirmed assets'))
    confirmed_system_user = serializers.ListField(child=serializers.UUIDField(),
                                                  source='meta.confirmed_system_user',
                                                  default=list, required=False,
                                                  label=_('Confirmed system user'))
    assets_waitlist = serializers.SerializerMethodField()
    system_user_waitlist = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        mini_fields = ['id']
        small_fields = [
            'title', 'status', 'action', 'date_created', 'date_updated',
            'type', 'type_display', 'action_display', 'ips', 'confirmed_assets',
            'date_start', 'date_expired', 'confirmed_system_user', 'hostname',
            'assets_waitlist', 'system_user_waitlist'
        ]
        m2m_fields = [
            'user', 'user_display', 'assignees', 'assignees_display',
            'assignee', 'assignee_display'
        ]

        fields = mini_fields + small_fields + m2m_fields
        read_only_fields = [
            'user_display', 'assignees_display', 'type', 'user', 'status',
            'date_created', 'date_updated', 'action', 'id', 'assignee',
            'assignee_display',
        ]
        extra_kwargs = {
            'status': {'label': _('Status')},
            'action': {'label': _('Action')},
            'user_display': {'label': _('User')}
        }

    def validate_assignees(self, assignees):
        count = current_org.org_admins().filter(id__in=[assignee.id for assignee in assignees]).count()
        if count != len(assignees):
            raise serializers.ValidationError(_('Must be organization admin or superuser'))
        return assignees

    def get_system_user_waitlist(self, instance: Ticket):
        """
        如果该字段数据量太大，需要分页，应该由前端直接请求 `system-user-list`
        """
        if not self._is_assignee(instance):
            return None
        return [{'id': sys_user.id, 'name': sys_user.name} for sys_user in SystemUser.objects.all()]

    def get_assets_waitlist(self, instance: Ticket):
        if not self._is_assignee(instance):
            return None

        assets = []
        meta = instance.meta
        ips = meta.get('ips', [])
        if ips:
            assets = Asset.objects.filter(ip__in=ips)

        hostname = meta.get('hostname')
        if not assets and hostname:
            # 如果有性能问题可以改为 `hostname__startswith`
            assets = Asset.objects.filter(hostname__icontains=hostname)
        return [{'id':asset.id, 'ip': asset.ip, 'hostname': asset.hostname} for asset in assets]

    def create(self, validated_data):
        validated_data['type'] = self.Meta.model.TYPE_REQUEST_ASSET_PERM
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

    def save(self, **kwargs):
        meta = self.validated_data.get('meta', {})
        date_start = meta.get('date_start')
        if date_start:
            meta['date_start'] = date_start.strftime('%Y-%m-%d %H:%M:%S%z')

        date_expired = meta.get('date_expired')
        if date_expired:
            meta['date_expired'] = date_expired.strftime('%Y-%m-%d %H:%M:%S%z')

        return super().save(**kwargs)

    def update(self, instance, validated_data):
        new_meta = validated_data['meta']
        if not self._is_assignee(instance):
            new_meta.pop('confirmed_assets', None)
            new_meta.pop('confirmed_system_user', None)
        old_meta = instance.meta
        meta = {}
        meta.update(old_meta)
        meta.update(new_meta)
        validated_data['meta'] = meta

        return super().update(instance, validated_data)

    def _is_assignee(self, obj: Ticket):
        user = self.context['request'].user
        return obj.is_assignee(user)
