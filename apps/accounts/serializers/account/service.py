from datetime import timedelta

from django.db.models import Count, Max, Q
from django.templatetags.static import static
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.models import CredentialClientInstance, IntegrationApplication
from acls.serializers.rules import ip_group_child_validator, ip_group_help_text
from common.serializers.fields import JSONManyToManyField
from common.utils import random_string
from orgs.mixins.serializers import BulkOrgResourceModelSerializer


class IntegrationApplicationSerializer(BulkOrgResourceModelSerializer):
    accounts = JSONManyToManyField(label=_('Account'))
    ip_group = serializers.ListField(
        default=['*'], label=_('Access IP'), help_text=ip_group_help_text,
        child=serializers.CharField(max_length=1024, validators=[ip_group_child_validator])
    )

    class Meta:
        model = IntegrationApplication
        fields_mini = ['id', 'name']
        fields_small = fields_mini + ['logo', 'accounts']
        fields = fields_small + [
            'date_last_used', 'date_created', 'date_updated',
            'ip_group', 'accounts_amount',
            'comment', 'is_active'
        ]
        extra_kwargs = {
            'comment': {'label': _('Comment')},
            'name': {'label': _('Name')},
            'accounts_amount': {'label': _('Accounts amount')},
            'is_active': {'default': True},
            'logo': {'required': False},
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not data.get('logo'):
            data['logo'] = static('img/logo.png')
        return data

    def create(self, validated_data):
        instance = super().create(validated_data)
        instance.refresh_secret()
        return instance


class IntegrationApplicationDetailSerializer(IntegrationApplicationSerializer):
    access_readiness = serializers.SerializerMethodField()

    class Meta(IntegrationApplicationSerializer.Meta):
        fields = IntegrationApplicationSerializer.Meta.fields + ['access_readiness']

    @staticmethod
    def get_access_readiness(instance):
        configurations = list(
            instance.access_configurations.filter(is_active=True)
            .prefetch_related('credentials')
        )
        allowed_ids = set(instance.get_accounts().values_list('id', flat=True))
        required_ids = {
            account_id
            for configuration in configurations
            for credential in configuration.credentials.all()
            for account_id in (credential.primary_account_id, credential.backup_account_id)
            if account_id
        }
        clients = CredentialClientInstance.objects.filter(
            application=instance, configuration__is_active=True, is_active=True,
        ).aggregate(
            instances_amount=Count('id', distinct=True),
            online_instances_amount=Count(
                'id', filter=Q(
                    date_last_seen__gte=timezone.now() - timedelta(minutes=2)
                ), distinct=True,
            ),
            last_fetched=Max('credential_statuses__date_fetched'),
        )
        first_configuration = configurations[0] if configurations else None
        return {
            'authorized_accounts_amount': len(allowed_ids),
            'active_configurations_amount': len(configurations),
            'missing_authorized_accounts_amount': len(required_ids - allowed_ids),
            'active_instances_amount': clients['instances_amount'],
            'online_instances_amount': clients['online_instances_amount'],
            'last_fetched': clients['last_fetched'],
            'configuration': (
                {'id': first_configuration.id, 'name': first_configuration.name}
                if first_configuration else None
            ),
        }


class IntegrationAccountSecretSerializer(serializers.Serializer):
    asset = serializers.CharField(required=False, allow_blank=True)
    asset_id = serializers.UUIDField(required=False, allow_null=True)
    account = serializers.CharField(required=False, allow_blank=True)
    account_id = serializers.UUIDField(required=False, allow_null=True)

    @staticmethod
    def _valid_at_least_one(attrs, fields):
        if not any(attrs.get(field) for field in fields):
            raise serializers.ValidationError(
                f"At least one of the following fields must be provided: {', '.join(fields)}."
            )

    def validate(self, attrs):
        if attrs.get('account_id'):
            return attrs

        self._valid_at_least_one(attrs, ['asset', 'asset_id'])
        self._valid_at_least_one(attrs, ['account', 'account_id'])
        return attrs
