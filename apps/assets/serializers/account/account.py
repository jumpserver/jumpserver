from django.db.models import F
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from common.drf.serializers import SecretReadableMixin
from assets.models import Account
from assets.serializers.base import AuthSerializerMixin
from .account_template import AccountTemplateSerializerMixin
from .common import BaseAccountSerializer


class AccountSerializer(
    AccountTemplateSerializerMixin, AuthSerializerMixin,
    BulkOrgResourceModelSerializer
):
    ip = serializers.ReadOnlyField(label=_("IP"))
    asset_name = serializers.ReadOnlyField(label=_("Asset"))
    platform = serializers.ReadOnlyField(label=_("Platform"))

    class Meta(BaseAccountSerializer.Meta):
        model = Account
        fields = BaseAccountSerializer.Meta.fields + ['account_template', ]

    def validate(self, attrs):
        attrs = self._validate_gen_key(attrs)
        attrs = super()._validate(attrs)
        return attrs

    @classmethod
    def setup_eager_loading(cls, queryset):
        """ Perform necessary eager loading of data. """
        queryset = queryset.prefetch_related('asset') \
            .annotate(ip=F('asset__ip')) \
            .annotate(asset_name=F('asset__name'))
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
            'systemuser_display': {'label': _('System user display')}
        }


class AccountTaskSerializer(serializers.Serializer):
    ACTION_CHOICES = (
        ('test', 'test'),
    )
    action = serializers.ChoiceField(choices=ACTION_CHOICES, write_only=True)
    task = serializers.CharField(read_only=True)
