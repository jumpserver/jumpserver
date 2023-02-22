from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from accounts.const import SecretType, Source
from accounts.models import Account, AccountTemplate
from accounts.tasks import push_accounts_to_assets_task
from assets.const import Category, AllTypes
from assets.models import Asset
from common.serializers import SecretReadableMixin, BulkModelSerializer
from common.serializers.fields import ObjectRelatedField, LabeledChoiceField
from .base import BaseAccountSerializer


class AccountSerializerCreateValidateMixin:
    from_id: str
    template: bool
    push_now: bool
    replace_attrs: callable

    def to_internal_value(self, data):
        from_id = data.pop('id', None)
        ret = super().to_internal_value(data)
        self.from_id = from_id
        return ret

    def set_secret(self, attrs):
        _id = self.from_id
        template = attrs.pop('template', None)

        if _id and template:
            account_template = AccountTemplate.objects.get(id=_id)
            attrs['secret'] = account_template.secret
        elif _id and not template:
            account = Account.objects.get(id=_id)
            attrs['secret'] = account.secret
        return attrs

    def validate(self, attrs):
        attrs = super().validate(attrs)
        return self.set_secret(attrs)

    @staticmethod
    def push_account(instance, push_now):
        if not push_now:
            return
        push_accounts_to_assets_task.delay([str(instance.id)])

    def create(self, validated_data):
        push_now = validated_data.pop('push_now', None)
        instance = super().create(validated_data)
        self.push_account(instance, push_now)
        return instance

    def update(self, instance, validated_data):
        # account cannot be modified
        validated_data.pop('username', None)
        push_now = validated_data.pop('push_now', None)
        instance = super().update(instance, validated_data)
        self.push_account(instance, push_now)
        return instance


class AccountSerializerCreateMixin(AccountSerializerCreateValidateMixin, BulkModelSerializer):
    template = serializers.BooleanField(
        default=False, label=_("Template"), write_only=True
    )
    push_now = serializers.BooleanField(
        default=False, label=_("Push now"), write_only=True
    )
    has_secret = serializers.BooleanField(label=_("Has secret"), read_only=True)


class AccountAssetSerializer(serializers.ModelSerializer):
    platform = ObjectRelatedField(read_only=True)
    category = LabeledChoiceField(choices=Category.choices, read_only=True, label=_('Category'))
    type = LabeledChoiceField(choices=AllTypes.choices(), read_only=True, label=_('Type'))

    class Meta:
        model = Asset
        fields = ['id', 'name', 'address', 'type', 'category', 'platform']

    def to_internal_value(self, data):
        if isinstance(data, dict):
            i = data.get('id')
        else:
            i = data

        try:
            return Asset.objects.get(id=i)
        except Asset.DoesNotExist:
            raise serializers.ValidationError(_('Asset not found'))


class AccountSerializer(AccountSerializerCreateMixin, BaseAccountSerializer):
    asset = AccountAssetSerializer(label=_('Asset'))
    source = LabeledChoiceField(choices=Source.choices, label=_("Source"), read_only=True)
    su_from = ObjectRelatedField(
        required=False, queryset=Account.objects, allow_null=True, allow_empty=True,
        label=_('Su from'), attrs=('id', 'name', 'username')
    )

    class Meta(BaseAccountSerializer.Meta):
        model = Account
        fields = BaseAccountSerializer.Meta.fields + [
            'su_from', 'asset', 'template',
            'push_now', 'source', 'connectivity'
        ]
        extra_kwargs = {
            **BaseAccountSerializer.Meta.extra_kwargs,
            'name': {'required': False, 'allow_null': True},
        }

    def validate_name(self, value):
        if not value:
            value = self.initial_data.get('username')
        return value

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('asset', 'asset__platform')
        return queryset


class AccountSecretSerializer(SecretReadableMixin, AccountSerializer):
    class Meta(AccountSerializer.Meta):
        extra_kwargs = {
            'secret': {'write_only': False},
        }


class AccountHistorySerializer(serializers.ModelSerializer):
    secret_type = LabeledChoiceField(choices=SecretType.choices, label=_('Secret type'))

    class Meta:
        model = Account.history.model
        fields = ['id', 'secret', 'secret_type', 'version', 'history_date', 'history_user']
        read_only_fields = fields


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
