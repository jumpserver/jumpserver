from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.drf.serializers import SecretReadableMixin
from common.drf.fields import ObjectRelatedField
from assets.models import Account, AccountTemplate, Asset
from assets.serializers.base import AuthValidateMixin
from .common import AccountFieldsSerializerMixin


class AccountSerializerCreateMixin(serializers.ModelSerializer):
    template = serializers.UUIDField(
        required=False, allow_null=True, write_only=True,
        label=_('Account template')
    )
    push_now = serializers.BooleanField(
        default=False, label=_("Push now"), write_only=True
    )

    @staticmethod
    def validate_template(value):
        try:
            return AccountTemplate.objects.get(id=value)
        except AccountTemplate.DoesNotExist:
            raise serializers.ValidationError(_('Account template not found'))

    @staticmethod
    def replace_attrs(account_template: AccountTemplate, attrs: dict):
        exclude_fields = [
            '_state', 'org_id', 'id', 'date_created', 'date_updated'
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
            # Todo: push it
            print("Start push account to asset")
        return instance


class AccountSerializer(
    AuthValidateMixin, AccountSerializerCreateMixin,
    AccountFieldsSerializerMixin, BulkOrgResourceModelSerializer
):
    asset = ObjectRelatedField(
        required=False, queryset=Asset.objects,
        label=_('Asset'), attrs=('id', 'name', 'ip')
    )
    platform = serializers.ReadOnlyField(label=_("Platform"))

    class Meta(AccountFieldsSerializerMixin.Meta):
        model = Account
        fields = AccountFieldsSerializerMixin.Meta.fields \
            + ['template', 'push_now']

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('asset')
        return queryset


class AccountSecretSerializer(SecretReadableMixin, AccountSerializer):
    class Meta(AccountSerializer.Meta):
        fields_backup = [
            'name', 'ip', 'platform', 'protocols', 'username', 'password',
            'private_key', 'public_key', 'date_created', 'date_updated', 'version'
        ]
        extra_kwargs = {
            'password': {'write_only': False},
            'private_key': {'write_only': False},
            'public_key': {'write_only': False},
        }


class AccountTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('test', 'test'),
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    task = serializers.CharField(read_only=True)
