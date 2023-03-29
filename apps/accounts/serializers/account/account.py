import uuid
from collections import defaultdict

from django.db import IntegrityError
from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from accounts.const import SecretType, Source, AccountExistPolicy
from accounts.models import Account, AccountTemplate
from accounts.tasks import push_accounts_to_assets_task
from assets.const import Category, AllTypes, Protocol
from assets.models import Asset
from common.serializers import SecretReadableMixin
from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from common.utils import get_logger
from .base import BaseAccountSerializer

logger = get_logger(__name__)


class AccountCreateUpdateSerializerMixin(serializers.Serializer):
    template = serializers.PrimaryKeyRelatedField(
        queryset=AccountTemplate.objects,
        required=False, label=_("Template"), write_only=True
    )
    push_now = serializers.BooleanField(
        default=False, label=_("Push now"), write_only=True
    )
    on_exist = LabeledChoiceField(
        choices=AccountExistPolicy.choices, default=AccountExistPolicy.ERROR,
        write_only=True, label=_('Exist policy')
    )

    class Meta:
        fields = ['template', 'push_now', 'on_exist']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_initial_value()

    def set_initial_value(self):
        if not getattr(self, 'initial_data', None):
            return
        if isinstance(self.initial_data, dict):
            initial_data = [self.initial_data]
        else:
            initial_data = self.initial_data

        for data in initial_data:
            if not data.get('asset'):
                raise serializers.ValidationError({'asset': 'Asset is required'})
            self.from_template_if_need(data)
            self.set_uniq_name_if_need(data)

    @staticmethod
    def set_uniq_name_if_need(initial_data):
        name = initial_data.get('name')
        if not name:
            name = initial_data.get('username')
        if Account.objects.filter(name=name, asset=initial_data['asset']).exists():
            name = name + '_' + uuid.uuid4().hex[:4]
        initial_data['name'] = name

    @staticmethod
    def from_template_if_need(initial_data):
        template_id = initial_data.pop('template', None)
        if not template_id:
            return
        if isinstance(template_id, (str, uuid.UUID)):
            template = AccountTemplate.objects.filter(id=template_id).first()
        else:
            template = template_id
        if not template:
            raise serializers.ValidationError({'template': 'Template not found'})

        # Set initial data from template
        ignore_fields = ['id', 'name', 'date_created', 'date_updated', 'org_id']
        field_names = [
            field.name for field in template._meta.fields
            if field.name not in ignore_fields
        ]
        attrs = {'source': 'template', 'source_id': template.id}
        for name in field_names:
            value = getattr(template, name, None)
            if value is None:
                continue
            attrs[name] = value
        initial_data.update(attrs)

    @staticmethod
    def push_account_if_need(instance, push_now, stat):
        if not push_now or stat != 'created':
            return
        push_accounts_to_assets_task.delay([str(instance.id)])

    def get_validators(self):
        _validators = super().get_validators()
        if getattr(self, 'initial_data', None) is None:
            return _validators
        on_exist = self.initial_data.get('on_exist')
        if on_exist == AccountExistPolicy.ERROR:
            return _validators
        _validators = [v for v in _validators if not isinstance(v, UniqueTogetherValidator)]
        return _validators

    @staticmethod
    def do_create(vd):
        on_exist = vd.pop('on_exist', None)

        q = Q()
        if vd.get('name'):
            q |= Q(name=vd['name'])
        if vd.get('username'):
            q |= Q(username=vd['username'], secret_type=vd.get('secret_type'))

        instance = Account.objects.filter(asset=vd['asset']).filter(q).first()
        # 不存在这个资产，不用关系策略
        if not instance:
            instance = Account.objects.create(**vd)
            return instance, 'created'

        if on_exist == AccountExistPolicy.SKIP:
            return instance, 'skipped'
        elif on_exist == AccountExistPolicy.UPDATE:
            for k, v in vd.items():
                setattr(instance, k, v)
            instance.save()
            return instance, 'updated'
        else:
            raise serializers.ValidationError({'non_field_error': 'Account already exists'})

    def create(self, validated_data):
        push_now = validated_data.pop('push_now', None)
        instance, stat = self.do_create(validated_data)
        self.push_account_if_need(instance, push_now, stat)
        return instance

    def update(self, instance, validated_data):
        # account cannot be modified
        validated_data.pop('username', None)
        validated_data.pop('on_exist', None)
        push_now = validated_data.pop('push_now', None)
        instance = super().update(instance, validated_data)
        self.push_account_if_need(instance, push_now, 'updated')
        return instance


class AccountAssetSerializer(serializers.ModelSerializer):
    platform = ObjectRelatedField(read_only=True)
    category = LabeledChoiceField(choices=Category.choices, read_only=True, label=_('Category'))
    type = LabeledChoiceField(choices=AllTypes.choices(), read_only=True, label=_('Type'))

    class Meta:
        model = Asset
        fields = ['id', 'name', 'address', 'type', 'category', 'platform', 'auto_info']

    def to_internal_value(self, data):
        if isinstance(data, dict):
            i = data.get('id') or data.get('pk')
        else:
            i = data

        try:
            return Asset.objects.get(id=i)
        except Asset.DoesNotExist:
            raise serializers.ValidationError(_('Asset not found'))


class AccountSerializer(AccountCreateUpdateSerializerMixin, BaseAccountSerializer):
    asset = AccountAssetSerializer(label=_('Asset'))
    source = LabeledChoiceField(choices=Source.choices, label=_("Source"), read_only=True)
    has_secret = serializers.BooleanField(label=_("Has secret"), read_only=True)
    su_from = ObjectRelatedField(
        required=False, queryset=Account.objects, allow_null=True, allow_empty=True,
        label=_('Su from'), attrs=('id', 'name', 'username')
    )

    class Meta(BaseAccountSerializer.Meta):
        model = Account
        fields = BaseAccountSerializer.Meta.fields + [
            'su_from', 'asset', 'version',
            'source', 'source_id', 'connectivity',
        ] + AccountCreateUpdateSerializerMixin.Meta.fields
        read_only_fields = BaseAccountSerializer.Meta.read_only_fields + [
            'source', 'source_id', 'connectivity'
        ]
        extra_kwargs = {
            **BaseAccountSerializer.Meta.extra_kwargs,
            'name': {'required': False},
        }

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related(
            'asset', 'asset__platform',
            'asset__platform__automation'
        )
        return queryset


class AssetAccountBulkSerializer(AccountCreateUpdateSerializerMixin, serializers.ModelSerializer):
    assets = serializers.PrimaryKeyRelatedField(queryset=Asset.objects, many=True, label=_('Assets'))

    class Meta:
        model = Account
        fields = [
            'name', 'username', 'secret', 'secret_type',
            'privileged', 'is_active', 'comment', 'template',
            'on_exist', 'push_now', 'assets',
        ]
        extra_kwargs = {
            'name': {'required': False},
            'secret_type': {'required': False},
        }

    def set_initial_value(self):
        if not getattr(self, 'initial_data', None):
            return
        initial_data = self.initial_data
        self.from_template_if_need(initial_data)

    @staticmethod
    def _validate_secret_type(assets, secret_type):
        if isinstance(assets, list):
            asset_ids = [a.id for a in assets]
            assets = Asset.objects.filter(id__in=asset_ids)
        asset_protocol = assets.prefetch_related('protocols').values_list('id', 'protocols__name')
        protocol_secret_types_map = Protocol.protocol_secret_types()
        asset_secret_types_mapp = defaultdict(set)

        for asset_id, protocol in asset_protocol:
            secret_types = set(protocol_secret_types_map.get(protocol, []))
            asset_secret_types_mapp[asset_id].update(secret_types)

        asset_support = {
            asset_id: secret_type in secret_types
            for asset_id, secret_types in asset_secret_types_mapp.items()
        }
        return asset_support

    @staticmethod
    def perform_create_account(vd, handler):
        lookup = {
            'username': vd['username'],
            'secret_type': vd.get('secret_type', 'password'),
        }
        if 'name' not in vd:
            vd['name'] = vd['username']
        try:
            instance, value = handler(defaults=vd, **lookup)
        except IntegrityError:
            vd['name'] = vd['name'] + '-' + str(uuid.uuid4())[:8]
            instance, value = handler(defaults=vd, **lookup)
        return instance, value

    def perform_bulk_create(self, validated_data):
        on_exist = validated_data.pop('on_exist', 'skip')
        assets = validated_data.pop('assets')
        secret_type = validated_data.get('secret_type', 'password')

        if on_exist == 'skip':
            handler = Account.objects.get_or_create
        else:
            handler = Account.objects.update_or_create

        result = {}
        asset_support_map = self._validate_secret_type(assets, secret_type)
        for asset in assets:
            if not asset_support_map[asset.id]:
                result[asset] = {'error': 'Asset does not support this secret type: %s' % secret_type}
                continue

            vd = validated_data.copy()
            vd['asset'] = asset
            try:
                instance, value = self.perform_create_account(vd, handler)
                result[asset] = {'changed': value}
            except Exception as e:
                result[asset] = {'error': str(e)}
        return result

    @staticmethod
    def push_accounts_if_need(result, push_now):
        pass

    def create(self, validated_data):
        push_now = validated_data.pop('push_now', False)
        result = self.perform_bulk_create(validated_data)
        self.push_accounts_if_need(result, push_now)
        result = {str(k): v for k, v in result.items()}
        return result


class AccountSecretSerializer(SecretReadableMixin, AccountSerializer):
    class Meta(AccountSerializer.Meta):
        extra_kwargs = {
            'secret': {'write_only': False},
        }


class AccountHistorySerializer(serializers.ModelSerializer):
    secret_type = LabeledChoiceField(choices=SecretType.choices, label=_('Secret type'))

    class Meta:
        model = Account.history.model
        fields = [
            'id', 'secret', 'secret_type', 'version',
            'history_date', 'history_user'
        ]
        read_only_fields = fields
        extra_kwargs = {
            'history_user': {'label': _('User')},
            'history_date': {'label': _('Date')},
        }


class AccountTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('test', 'test'),
        ('verify', 'verify'),
        ('push', 'push'),
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    accounts = serializers.PrimaryKeyRelatedField(
        queryset=Account.objects, required=False, allow_empty=True, many=True
    )
    task = serializers.CharField(read_only=True)
