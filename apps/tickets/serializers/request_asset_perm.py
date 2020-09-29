from itertools import chain

from rest_framework import serializers
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse
from django.db.models import Q

from common.utils.timezone import dt_parser, dt_formater
from orgs.utils import tmp_to_root_org
from orgs.models import Organization, ROLE as ORG_ROLE
from assets.models.asset import Asset
from users.models.user import User
from perms.serializers import ActionsField
from perms.models import Action
from ..models import Ticket


class RequestAssetPermTicketSerializer(serializers.ModelSerializer):
    actions = ActionsField(source='meta.actions', choices=Action.DB_CHOICES,
                           default=Action.CONNECT)
    ips = serializers.ListField(child=serializers.IPAddressField(), source='meta.ips',
                                default=list, label=_('IP group'))
    hostname = serializers.CharField(max_length=256, source='meta.hostname', default='',
                                     allow_blank=True, label=_('Hostname'))
    system_user = serializers.CharField(max_length=256, source='meta.system_user', default='',
                                        allow_blank=True, label=_('System user'))
    date_start = serializers.DateTimeField(source='meta.date_start', allow_null=True,
                                           required=False, label=_('Date start'))
    date_expired = serializers.DateTimeField(source='meta.date_expired', allow_null=True,
                                             required=False, label=_('Date expired'))
    confirmed_assets = serializers.ListField(child=serializers.UUIDField(),
                                             source='meta.confirmed_assets',
                                             default=list, required=False,
                                             label=_('Confirmed assets'))
    confirmed_system_users = serializers.ListField(child=serializers.UUIDField(),
                                                  source='meta.confirmed_system_users',
                                                  default=list, required=False,
                                                  label=_('Confirmed system user'))
    assets_waitlist_url = serializers.SerializerMethodField()
    system_users_waitlist_url = serializers.SerializerMethodField()

    class Meta:
        model = Ticket
        mini_fields = ['id', 'title']
        small_fields = [
            'status', 'action', 'date_created', 'date_updated', 'system_users_waitlist_url',
            'type', 'type_display', 'action_display', 'ips', 'confirmed_assets',
            'date_start', 'date_expired', 'confirmed_system_users', 'hostname',
            'assets_waitlist_url', 'system_user', 'org_id', 'actions', 'comment'
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
            'user_display': {'label': _('User')},
            'org_id': {'required': True}
        }

    def validate(self, attrs):
        org_id = attrs.get('org_id')
        assignees = attrs.get('assignees')

        instance = self.instance
        if instance is not None:
            if org_id and not assignees:
                assignees = list(instance.assignees.all())
            elif assignees and not org_id:
                org_id = instance.org_id
            elif assignees and org_id:
                pass
            else:
                return attrs

        user = self.context['request'].user
        org = Organization.get_instance(org_id)
        if org is None:
            raise serializers.ValidationError(_('Invalid `org_id`'))

        q = Q(role=User.ROLE.ADMIN)
        if not org.is_default():
            q |= Q(m2m_org_members__role=ORG_ROLE.ADMIN, orgs__id=org_id, orgs__members=user)

        q &= Q(id__in=[assignee.id for assignee in assignees])
        count = User.objects.filter(q).distinct().count()
        if count != len(assignees):
            raise serializers.ValidationError(_('Field `assignees` must be organization admin or superuser'))
        return attrs

    def get_system_users_waitlist_url(self, instance: Ticket):
        if not self._is_assignee(instance):
            return None
        return reverse('api-assets:system-user-list')

    def get_assets_waitlist_url(self, instance: Ticket):
        if not self._is_assignee(instance):
            return None

        asset_api = reverse('api-assets:asset-list')
        query = ''

        meta = instance.meta
        hostname = meta.get('hostname')
        if hostname:
            query = '?search=%s' % hostname

        return asset_api + query

    def _recommend_assets(self, data, instance):
        confirmed_assets = data.get('confirmed_assets')
        if not confirmed_assets and self._is_assignee(instance):
            ips = data.get('ips')
            hostname = data.get('hostname')
            limit = 5

            q = Q(id=None)
            if ips:
                limit = len(ips) + 2
                q |= Q(ip__in=ips)
            if hostname:
                q |= Q(hostname__icontains=hostname)

            data['confirmed_assets'] = list(
                map(lambda x: str(x), chain(*Asset.objects.filter(q)[0: limit].values_list('id'))))

    def to_representation(self, instance):
        data = super().to_representation(instance)
        self._recommend_assets(data, instance)
        return data

    def _create_body(self, validated_data):
        meta = validated_data['meta']
        type = Ticket.TYPE.get(validated_data.get('type', ''))
        date_start = dt_parser(meta.get('date_start')).strftime(settings.DATETIME_DISPLAY_FORMAT)
        date_expired = dt_parser(meta.get('date_expired')).strftime(settings.DATETIME_DISPLAY_FORMAT)

        validated_data['body'] = _('''
        Type: {type}<br>
        User: {username}<br>
        Ip group: {ips}<br>
        Hostname: {hostname}<br>
        System user: {system_user}<br>
        Date start: {date_start}<br>
        Date expired: {date_expired}<br>
        ''').format(
            type=type,
            username=validated_data.get('user', ''),
            ips=', '.join(meta.get('ips', [])),
            hostname=meta.get('hostname', ''),
            system_user=meta.get('system_user', ''),
            date_start=date_start,
            date_expired=date_expired
        )

    def create(self, validated_data):
        # `type` 与 `user` 用户不可提交，
        validated_data['type'] = self.Meta.model.TYPE.REQUEST_ASSET_PERM
        validated_data['user'] = self.context['request'].user
        # `confirmed` 相关字段只能审批人修改，所以创建时直接清理掉
        self._pop_confirmed_fields()
        self._create_body(validated_data)
        return super().create(validated_data)

    def save(self, **kwargs):
        """
        做了一些数据转换
        """
        meta = self.validated_data.get('meta', {})

        org_id = self.validated_data.get('org_id')
        if org_id is not None and org_id == Organization.DEFAULT_ID:
            self.validated_data['org_id'] = ''

        # 时间的转换，好烦😭，可能有更好的办法吧
        date_start = meta.get('date_start')
        if date_start:
            meta['date_start'] = dt_formater(date_start)

        date_expired = meta.get('date_expired')
        if date_expired:
            meta['date_expired'] = dt_formater(date_expired)

        # UUID 的转换
        confirmed_system_users = meta.get('confirmed_system_users')
        if confirmed_system_users:
            meta['confirmed_system_users'] = [str(system_user) for system_user in confirmed_system_users]

        confirmed_assets = meta.get('confirmed_assets')
        if confirmed_assets:
            meta['confirmed_assets'] = [str(asset) for asset in confirmed_assets]

        with tmp_to_root_org():
            return super().save(**kwargs)

    def update(self, instance, validated_data):
        new_meta = validated_data['meta']
        if not self._is_assignee(instance):
            self._pop_confirmed_fields()

        # Json 字段保存的坑😭
        old_meta = instance.meta
        meta = {}
        meta.update(old_meta)
        meta.update(new_meta)
        validated_data['meta'] = meta

        return super().update(instance, validated_data)

    def _pop_confirmed_fields(self):
        meta = self.validated_data['meta']
        meta.pop('confirmed_assets', None)
        meta.pop('confirmed_system_users', None)

    def _is_assignee(self, obj: Ticket):
        user = self.context['request'].user
        return obj.is_assignee(user)


class AssigneeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    username = serializers.CharField()
