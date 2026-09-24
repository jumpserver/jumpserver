from datetime import timedelta

from django.db.models import Count, Max, Q
from django.templatetags.static import static
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import ApplicationEvent, WebhookRequestMethod
from accounts.models import ApplicationWebhook, CredentialClientInstance, IntegrationApplication
from accounts.webhooks import (
    WebhookValidationError, mask_webhook_url, validate_webhook_headers,
    validate_webhook_template, validate_webhook_url,
)
from acls.serializers.rules import ip_group_child_validator, ip_group_help_text
from common.serializers.fields import JSONManyToManyField, ListMultipleChoiceField, ObjectRelatedField
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
            for account_id in (credential.account_id, credential.alternate_account_id)
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


class ApplicationWebhookSerializer(serializers.ModelSerializer):
    applications = ObjectRelatedField(
        queryset=IntegrationApplication.objects, many=True,
        attrs=('id', 'name'), label=_('Integration applications'),
    )
    url = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=2048,
    )
    headers = serializers.DictField(
        child=serializers.CharField(allow_blank=True, max_length=4096),
        write_only=True, required=False,
    )
    method = serializers.ChoiceField(choices=WebhookRequestMethod.choices)
    events = ListMultipleChoiceField(choices=ApplicationEvent.choices)
    body_template = serializers.JSONField()
    url_display = serializers.SerializerMethodField()
    header_names = serializers.SerializerMethodField()

    class Meta:
        model = ApplicationWebhook
        fields = [
            'id', 'name', 'applications', 'is_active', 'url', 'url_display',
            'method', 'headers', 'header_names', 'events', 'body_template',
            'date_created', 'date_updated', 'comment',
        ]
        read_only_fields = ['id', 'url_display', 'header_names']

    @staticmethod
    def _validation_error(exc):
        raise serializers.ValidationError(str(exc))

    def validate_url(self, value):
        if not value:
            return ''
        try:
            return validate_webhook_url(value)
        except WebhookValidationError as exc:
            self._validation_error(exc)

    def validate_headers(self, value):
        try:
            return validate_webhook_headers(value)
        except WebhookValidationError as exc:
            self._validation_error(exc)

    def validate_body_template(self, value):
        try:
            return validate_webhook_template(value)
        except WebhookValidationError as exc:
            self._validation_error(exc)

    def validate(self, attrs):
        instance = self.instance
        enabled = attrs.get('is_active', getattr(instance, 'is_active', False))
        url = attrs.get('url', getattr(instance, 'url', ''))
        events = attrs.get('events', getattr(instance, 'events', []))
        applications = attrs.get('applications')
        if applications is None and instance and instance.pk:
            applications = instance.applications.all()
        if not applications:
            raise serializers.ValidationError({'applications': _('Select at least one application.')})
        if enabled and not url:
            raise serializers.ValidationError({'url': _('URL is required when webhook is enabled.')})
        if enabled and not events:
            raise serializers.ValidationError({'events': _('Select at least one event.')})
        return attrs

    @staticmethod
    def get_url_display(instance):
        return mask_webhook_url(instance.url)

    @staticmethod
    def get_header_names(instance):
        return sorted(instance.headers)
