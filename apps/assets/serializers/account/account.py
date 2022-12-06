from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from common.drf.serializers import SecretReadableMixin
from common.drf.fields import ObjectRelatedField, LabeledChoiceField
from assets.tasks import push_accounts_to_assets
from assets.models import Account, AccountTemplate, Asset
from .base import BaseAccountSerializer
from assets.const import SecretType


class AccountSerializerCreateMixin(serializers.ModelSerializer):
    template = serializers.UUIDField(
        required=False, allow_null=True, write_only=True,
        label=_('Account template')
    )
    push_now = serializers.BooleanField(
        default=False, label=_("Push now"), write_only=True
    )
    has_secret = serializers.BooleanField(label=_("Has secret"), read_only=True)

    @staticmethod
    def validate_template(value):
        try:
            return AccountTemplate.objects.get(id=value)
        except AccountTemplate.DoesNotExist:
            raise serializers.ValidationError(_('Account template not found'))

    @staticmethod
    def replace_attrs(account_template: AccountTemplate, attrs: dict):
        exclude_fields = [
            '_state', 'org_id', 'id', 'date_created',
            'date_updated'
        ]
        template_attrs = {
            k: v for k, v in account_template.__dict__.items()
            if k not in exclude_fields
        }
        for k, v in template_attrs.items():
            attrs.setdefault(k, v)

    def validate(self, attrs):
        account_template = attrs.pop('template', None)
        if account_template:
            self.replace_attrs(account_template, attrs)
        self.push_now = attrs.pop('push_now', False)
        return super().validate(attrs)

    def create(self, validated_data):
        instance = super().create(validated_data)
        if self.push_now:
            push_accounts_to_assets.delay([instance.id], [instance.asset_id])
        return instance


class AccountSerializer(AccountSerializerCreateMixin, BaseAccountSerializer):
    asset = ObjectRelatedField(
        required=False, queryset=Asset.objects,
        label=_('Asset'), attrs=('id', 'name', 'address', 'platform_id')
    )
    su_from = ObjectRelatedField(
        required=False, queryset=Account.objects, allow_null=True, allow_empty=True,
        label=_('Account'), attrs=('id', 'name', 'username')
    )

    class Meta(BaseAccountSerializer.Meta):
        model = Account
        fields = BaseAccountSerializer.Meta.fields \
            + ['su_from', 'version', 'asset'] \
            + ['template', 'push_now']
        extra_kwargs = {
            **BaseAccountSerializer.Meta.extra_kwargs,
            'name': {'required': False, 'allow_null': True},
        }

    def __init__(self, *args, data=None, **kwargs):
        super().__init__(*args, data=data, **kwargs)
        if data and 'name' not in data:
            username = data.get('username')
            if username is not None:
                data['name'] = username
        if hasattr(self, 'initial_data') and \
                not getattr(self, 'initial_data', None):
            delattr(self, 'initial_data')

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
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    task = serializers.CharField(read_only=True)
