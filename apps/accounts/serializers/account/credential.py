import re

from accounts.credential_client.documentation import sdk_languages
from accounts.models import (
    Account,
    ApplicationCredential,
    CredentialApplicationBinding,
    CredentialClientInstance,
    CredentialClientStatus,
    IntegrationApplication,
)
from common.serializers.fields import ObjectRelatedField
from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from rest_framework import serializers

__all__ = [
    'ApplicationCredentialSerializer', 'ApplicationCredentialListSerializer',
    'CredentialApplicationBindingSerializer',
    'CredentialClientInstanceSerializer', 'CredentialClientStatusSerializer',
    'CredentialFetchSerializer', 'AuthorizedAccountsSerializer',
    'CredentialConfirmSerializer', 'CredentialAgentRegisterSerializer',
    'CredentialAgentSyncSerializer',
    'CredentialAccessWizardSerializer',
    'CredentialChangeRetrySerializer', 'CredentialRotationReasonSerializer',
]


SYSTEMD_UNIT = re.compile(r'^[A-Za-z0-9_.@:-]+\.service$')
DELIVERY_MODES = [('json', _('JSON files')), ('environment', _('Environment files')), ('socket', _('Unix socket'))]
SYSTEMD_ACTIONS = [('reload', _('Reload')), ('restart', _('Restart'))]


class CredentialRotationReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=512, required=False, default='', allow_blank=True)


class CredentialChangeRetrySerializer(CredentialRotationReasonSerializer):
    execution_id = serializers.UUIDField()
    reason = serializers.CharField(max_length=512, allow_blank=False)


class SubscribedAccountField(ObjectRelatedField):
    asset_field = ObjectRelatedField(read_only=True, attrs=('id', 'name', 'address'))

    def to_representation(self, value):
        data = super().to_representation(value)
        data['asset'] = self.asset_field.to_representation(value.asset)
        return data

    def _get_openapi_object_schema(self):
        schema = super()._get_openapi_object_schema()
        schema['properties']['asset'] = self.asset_field.get_schema()
        return schema


class ApplicationCredentialSerializer(BulkOrgResourceModelSerializer):
    rotation = serializers.SerializerMethodField()
    precheck = serializers.SerializerMethodField()
    preparation = serializers.SerializerMethodField()
    standby_no_traffic_days = serializers.IntegerField(
        source='source_no_traffic_days', min_value=1, max_value=3650,
        required=False, help_text=_('Deprecated alias for source_no_traffic_days.'),
    )

    @staticmethod
    def get_preparation(instance):
        from accounts.credential_rotation.preparation import info
        return info(instance) if instance.mode == ApplicationCredential.Mode.alternating_rotation else None

    @staticmethod
    def get_precheck(instance):
        from accounts.credential_rotation.preflight import info
        return info(instance) if instance.mode == ApplicationCredential.Mode.alternating_rotation else None

    @staticmethod
    def get_rotation(instance):
        from accounts.credential_rotation.execution import execution_info
        return execution_info(instance)

    account = ObjectRelatedField(
        queryset=Account.objects, attrs=('id', 'name', 'username', 'secret_type'),
        label=_('Account'), required=False, allow_null=True
    )
    alternate_account = ObjectRelatedField(
        queryset=Account.objects, attrs=('id', 'name', 'username'),
        label=_('Alternate account'), required=False, allow_null=True
    )
    active_account = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'username'),
        label=_('Active account')
    )
    asset = serializers.SerializerMethodField(label=_('Asset'))
    applications_amount = serializers.IntegerField(read_only=True)
    blockers = serializers.SerializerMethodField(label=_('Blockers'))
    applications = ObjectRelatedField(
        queryset=IntegrationApplication.objects, many=True, required=True,
        attrs=('id', 'name'), label=_('Integration applications')
    )
    subscription_accounts = SubscribedAccountField(
        queryset=Account.objects, many=True, required=False,
        attrs=('id', 'name', 'username', 'asset_id'), label=_('Subscribed accounts'),
    )
    change_execution = ObjectRelatedField(read_only=True, attrs=('id', 'status', 'date_finished'))

    class Meta:
        model = ApplicationCredential
        fields_mini = ['id', 'name', 'key']
        fields_small = fields_mini + [
            'mode', 'asset', 'account', 'alternate_account', 'subscription_accounts',
            'subscription_all_authorized',
            'active_account', 'revision', 'status', 'is_active',
            'source_no_traffic_days', 'standby_no_traffic_days',
            'date_last_rotated', 'applications_amount',
        ]
        fields = fields_small + [
            'applications', 'change_execution', 'rotation', 'precheck', 'preparation', 'blockers',
            'rotation_cancelled', 'date_rotation_started',
            'date_created', 'date_updated', 'created_by', 'comment',
        ]
        read_only_fields = [
            'key', 'active_account', 'revision', 'status',
            'applications_amount', 'blockers',
            'subscription_all_authorized',
            'rotation_cancelled', 'date_rotation_started', 'date_last_rotated',
        ]

    @classmethod
    def setup_eager_loading(cls, queryset):
        return queryset.select_related(
            'account__asset__platform', 'alternate_account', 'active_account', 'change_execution'
        ).prefetch_related(
            'applications',
            Prefetch('subscription_accounts', queryset=Account.objects.select_related('asset')),
        ).annotate(
            applications_amount=Count('applications', distinct=True),
        )

    @staticmethod
    def get_asset(instance):
        asset = instance.asset
        if not asset:
            return None
        return {
            'id': str(asset.id),
            'name': asset.name,
            'address': asset.address,
            'platform': {
                'id': str(asset.platform_id),
                'name': asset.platform.name,
                'category': asset.platform.category,
                'type': asset.platform.type,
            },
        }

    @staticmethod
    def get_blockers(instance):
        if instance.status == ApplicationCredential.Status.idle:
            return []
        return instance.get_blockers()

    def validate(self, attrs):
        initial = getattr(self, 'initial_data', {})
        if 'source_no_traffic_days' in initial and 'standby_no_traffic_days' in initial:
            raise serializers.ValidationError({
                'source_no_traffic_days': _('Use only one no-secret-fetch duration field.'),
            })
        from accounts.credential_rotation.preflight import check_ownership
        attrs = self.validate_accounts(attrs)
        accounts = [
            attrs.get('account', getattr(self.instance, 'account', None)),
            attrs.get('alternate_account', getattr(self.instance, 'alternate_account', None)),
        ]
        mode = attrs.get('mode') or getattr(
            self.instance, 'mode', ApplicationCredential.Mode.subscription
        )
        if mode == ApplicationCredential.Mode.alternating_rotation:
            check_ownership(self.instance or ApplicationCredential(), accounts)
        applications = attrs.get('applications')
        if applications is None and self.instance:
            applications = list(self.instance.applications.all())
        if not applications:
            raise serializers.ValidationError({'applications': _('Select at least one application.')})
        if mode == ApplicationCredential.Mode.subscription:
            selected = attrs.get('subscription_accounts')
            if selected is None and self.instance:
                selected = list(self.instance.subscription_accounts.all())
            if not selected and not (
                self.instance and self.instance.subscription_all_authorized
                and 'subscription_accounts' not in attrs
            ):
                raise serializers.ValidationError({'subscription_accounts': _(
                    'Select at least one account to subscribe to.'
                )})
            if selected:
                required = {item.id for item in selected}
                unauthorized = [
                    application.name for application in applications
                    if not required.issubset(set(application.get_accounts().values_list('id', flat=True)))
                ]
                if unauthorized:
                    raise serializers.ValidationError({'subscription_accounts': _(
                        'These applications are not authorized for every subscribed account: {names}'
                    ).format(names=', '.join(unauthorized))})
            if 'subscription_accounts' in attrs:
                attrs['subscription_all_authorized'] = False
        elif attrs.get('subscription_accounts'):
            raise serializers.ValidationError({'subscription_accounts': _(
                'Subscribed accounts are only available for credential change subscriptions.'
            )})
        if mode == ApplicationCredential.Mode.alternating_rotation:
            required = {item.id for item in accounts if item}
            unauthorized = [
                application.name for application in applications
                if not required.issubset(set(application.get_accounts().values_list('id', flat=True)))
            ]
            if unauthorized:
                raise serializers.ValidationError({'applications': _(
                    'These applications are not authorized for every credential account: {names}'
                ).format(names=', '.join(unauthorized))})
        return attrs

    def validate_accounts(self, attrs):
        if self.instance and self.instance.status != ApplicationCredential.Status.idle:
            for field in ('account', 'alternate_account', 'is_active', 'source_no_traffic_days'):
                if field in attrs and attrs[field] != getattr(self.instance, field):
                    raise serializers.ValidationError(_('Credential settings cannot be changed during rotation.'))
            if 'applications' in attrs and {
                item.id for item in attrs['applications']
            } != set(self.instance.applications.values_list('id', flat=True)):
                raise serializers.ValidationError(_('Credential settings cannot be changed during rotation.'))
        if self.instance and 'mode' in attrs and attrs['mode'] != self.instance.mode:
            raise serializers.ValidationError({'mode': _('The credential policy mode cannot be changed.')})
        account = attrs.get('account') or getattr(self.instance, 'account', None)
        mode = attrs.get('mode') or getattr(self.instance, 'mode', ApplicationCredential.Mode.subscription)
        alternate = attrs.get('alternate_account', getattr(self.instance, 'alternate_account', None))
        if mode == ApplicationCredential.Mode.subscription:
            attrs['account'] = None
            attrs['alternate_account'] = None
            attrs['active_account'] = None
            return attrs
        if not account:
            raise serializers.ValidationError({'account': _(
                'This field is required for alternating dual-account rotation.'
            )})
        if not alternate:
            raise serializers.ValidationError({'alternate_account': _(
                'This field is required for alternating dual-account rotation.'
            )})
        if not account:
            return attrs
        if account.id == alternate.id:
            raise serializers.ValidationError(_('The initial and alternate accounts must be different.'))
        if account.asset_id != alternate.asset_id:
            raise serializers.ValidationError(_('The initial and alternate accounts must belong to the same asset.'))
        if account.org_id != alternate.org_id:
            raise serializers.ValidationError(_('The initial and alternate accounts must belong to the same organization.'))
        if account.secret_type != alternate.secret_type:
            raise serializers.ValidationError(_('The initial and alternate accounts must use the same secret type.'))
        return attrs

    @staticmethod
    def sync_applications(instance, applications):
        from accounts.const import ApplicationEvent, AuditEvent
        from accounts.credential_client.audit import record
        from accounts.credential_client.events import enqueue

        wanted = {application.id: application for application in applications}
        removed = list(instance.application_bindings.exclude(
            application_id__in=wanted
        ).select_related('application'))
        instance.application_bindings.filter(id__in=[item.id for item in removed]).delete()
        existing = set(instance.application_bindings.values_list('application_id', flat=True))
        added = [
            CredentialApplicationBinding(
                credential=instance, application=application, org_id=instance.org_id,
            )
            for application_id, application in wanted.items() if application_id not in existing
        ]
        CredentialApplicationBinding.objects.bulk_create(added)
        from accounts.credential_client.access import publish_application_scope
        for application in (binding.application for binding in added):
            publish_application_scope(application)
        for binding in added:
            event = record(
                AuditEvent.AUTHORIZATION_GRANTED, credential=instance,
                application=binding.application,
            )
            enqueue(event, ApplicationEvent.CREDENTIAL_UPDATED)

    def create(self, validated_data):
        from accounts.credential_rotation.preflight import check_ownership
        applications = validated_data.pop('applications')
        accounts = [validated_data.get('account'), validated_data.get('alternate_account')]
        # Lock shared accounts before inserting a new credential, then recheck ownership.
        with transaction.atomic():
            list(Account.objects.select_for_update().filter(
                pk__in=[a.pk for a in accounts if a],
            ).order_by('id'))
            if validated_data.get('mode', ApplicationCredential.Mode.subscription) == ApplicationCredential.Mode.alternating_rotation:
                check_ownership(ApplicationCredential(), accounts)
                validated_data['active_account'] = validated_data['account']
            instance = super().create(validated_data)
            self.sync_applications(instance, applications)
            return instance

    @transaction.atomic
    def update(self, instance, validated_data):
        from accounts.credential_rotation.preflight import check_ownership
        instance = ApplicationCredential.objects.select_for_update().get(pk=instance.pk)
        # Recheck stage constraints against the locked, current credential.
        self.instance = instance
        validated_data = self.validate(validated_data)
        applications = validated_data.pop('applications', None)
        previous_accounts = set(instance.subscription_accounts.values_list('id', flat=True))
        previous_all = instance.subscription_all_authorized
        account = validated_data.get('account', instance.account)
        accounts = [account, validated_data.get('alternate_account', instance.alternate_account)]
        # Existing bindings already exclude competing claims. Lock only newly
        # acquired accounts, avoiding lock inversion with subscription publication.
        existing_ids = {instance.account_id, instance.alternate_account_id}
        list(Account.objects.select_for_update().filter(
            pk__in=[a.pk for a in accounts if a and a.pk not in existing_ids],
        ).order_by('id'))
        if instance.mode == ApplicationCredential.Mode.alternating_rotation:
            check_ownership(instance, accounts)
        if account and instance.active_account_id not in {item.id for item in accounts if item}:
            validated_data['active_account'] = account
            validated_data['revision'] = instance.revision + 1
        instance = super().update(instance, validated_data)
        if applications is not None:
            self.sync_applications(instance, applications)
        if instance.mode == ApplicationCredential.Mode.subscription and (
            previous_all != instance.subscription_all_authorized
            or previous_accounts != set(instance.subscription_accounts.values_list('id', flat=True))
        ):
            from accounts.const import ApplicationEvent, AuditEvent
            from accounts.credential_client.audit import record
            from accounts.credential_client.events import enqueue
            event = record(AuditEvent.CONFIGURATION_UPDATED, credential=instance)
            enqueue(event, ApplicationEvent.CONFIGURATION_UPDATED)
        return instance


class ApplicationCredentialListSerializer(ApplicationCredentialSerializer):
    subscription_accounts_amount = serializers.IntegerField(read_only=True)
    subscription_assets_amount = serializers.IntegerField(read_only=True)
    subscription_accounts_preview = SubscribedAccountField(
        read_only=True, many=True, attrs=('id', 'name', 'username', 'asset_id'),
    )

    class Meta(ApplicationCredentialSerializer.Meta):
        fields_small = [
            field for field in ApplicationCredentialSerializer.Meta.fields_small
            if field != 'subscription_accounts'
        ] + [
            'subscription_accounts_amount', 'subscription_assets_amount',
            'subscription_accounts_preview',
        ]
        fields = fields_small
        relation_count_fields = {'applications_amount': 'applications'}

    @classmethod
    def setup_eager_loading(cls, queryset):
        # Keep the list payload bounded: count the scope and fetch at most three
        # accounts per policy. Application counts use the batch helper.
        return queryset.select_related(
            'account__asset__platform', 'alternate_account', 'active_account',
        ).prefetch_related(
            Prefetch(
                'subscription_accounts',
                queryset=Account.objects.select_related('asset').only(
                    'id', 'name', 'username', 'asset_id',
                    'asset__id', 'asset__name', 'asset__address',
                ).order_by('name', 'username', 'id')[:3],
                to_attr='subscription_accounts_preview',
            ),
        ).annotate(
            subscription_accounts_amount=Count('subscription_accounts', distinct=True),
            subscription_assets_amount=Count('subscription_accounts__asset_id', distinct=True),
        )


class CredentialClientStatusSerializer(serializers.ModelSerializer):
    credential = serializers.SerializerMethodField(label=_('Credential policy'))
    applied_account = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'username'), label=_('Applied account')
    )

    class Meta:
        model = CredentialClientStatus
        fields = [
            'id', 'credential', 'fetched_revision', 'delivered_revision', 'applied_revision',
            'applied_account', 'required_revision', 'is_rotation_participant',
            'date_last_seen', 'date_fetched', 'date_delivered', 'date_applied',
        ]
        read_only_fields = fields

    @staticmethod
    def get_credential(instance):
        credential = instance.binding.credential
        return {
            'id': str(credential.id), 'name': credential.name,
            'key': credential.key, 'status': credential.status, 'mode': credential.mode,
        }


class CredentialClientInstanceSerializer(BulkOrgResourceModelSerializer):
    credentials = ObjectRelatedField(
        source='application.application_credentials', many=True, read_only=True, attrs=('id', 'name'),
    )
    application = ObjectRelatedField(
        read_only=True, attrs=('id', 'name'), label=_('Integration application')
    )
    online = serializers.SerializerMethodField(label=_('Online'))
    credential_statuses = CredentialClientStatusSerializer(many=True, read_only=True)
    configuration_current = serializers.SerializerMethodField()
    upgrade_required = serializers.SerializerMethodField()
    reason = serializers.CharField(
        write_only=True, required=False, allow_blank=True, max_length=512,
    )

    class Meta:
        model = CredentialClientInstance
        fields_mini = ['id', 'instance_id', 'type']
        fields_small = fields_mini + [
            'application', 'online', 'date_last_seen', 'is_active',
        ]
        fields = fields_small + [
            'client_version', 'protocol_version', 'config_schema_version',
            'config_digest', 'configuration_current', 'upgrade_required',
            'sync_status', 'sync_error', 'date_last_synced',
            'credential_statuses', 'credentials', 'reason', 'date_created', 'date_updated', 'comment',
        ]
        read_only_fields = [
            'id', 'instance_id', 'type', 'application', 'online',
            'client_version', 'protocol_version', 'config_schema_version',
            'config_digest', 'configuration_current', 'upgrade_required',
            'sync_status', 'sync_error', 'date_last_synced',
            'date_last_seen', 'credential_statuses', 'date_created', 'date_updated',
        ]

    @staticmethod
    def get_online(instance):
        return bool(instance.online and instance.is_valid)

    @staticmethod
    def get_configuration_current(instance):
        if instance.type != CredentialClientInstance.Type.agent or not instance.config_digest:
            return None
        from accounts.credential_client.manager import CredentialClientManager
        return instance.config_digest == CredentialClientManager.agent_configuration_digest(
            instance.application, instance.delivery_scope
        )

    @staticmethod
    def get_upgrade_required(instance):
        return instance.protocol_version != 1 or (
            instance.type == CredentialClientInstance.Type.agent
            and instance.config_schema_version != 1
        )

    def validate(self, attrs):
        if (
            self.instance and self.instance.is_active
            and attrs.get('is_active') is False
            and self.instance.credential_statuses.exclude(
                binding__credential__status=ApplicationCredential.Status.idle,
            ).exists()
            and not attrs.get('reason', '').strip()
        ):
            raise serializers.ValidationError({
                'reason': _('Explain why the rotating client should be excluded.')
            })
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        reason = validated_data.pop('reason', '').strip()
        if instance.is_active and validated_data.get('is_active') is False:
            from accounts.credential_rotation.participants import exclude

            credential_ids = list(instance.credential_statuses.exclude(
                binding__credential__status=ApplicationCredential.Status.idle,
            ).values_list('binding__credential_id', flat=True))
            locked_credentials = ApplicationCredential.objects.select_for_update().filter(
                id__in=credential_ids,
            ).order_by('id')
            credentials = {credential.id: credential for credential in locked_credentials}
            states = list(CredentialClientStatus.objects.select_for_update(of=('self',)).select_related(
                'binding__credential', 'binding__application',
                'applied_account',
            ).filter(client=instance, binding__credential_id__in=credentials))
            for credential_id, credential in credentials.items():
                exclude(
                    credential,
                    [state for state in states if state.binding.credential_id == credential_id],
                    reason,
                )
        instance._application_audit_summary = reason
        try:
            return super().update(instance, validated_data)
        finally:
            del instance._application_audit_summary


class CredentialApplicationBindingSerializer(BulkOrgResourceModelSerializer):
    credential = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'key', 'status'),
        label=_('Credential policy')
    )
    application = ObjectRelatedField(
        read_only=True, attrs=('id', 'name'),
        label=_('Integration application')
    )
    clients_amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = CredentialApplicationBinding
        fields = [
            'id', 'credential', 'application', 'clients_amount',
            'date_created', 'date_updated', 'comment',
        ]
        read_only_fields = fields


class CredentialFetchSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64, required=False)
    account_id = serializers.UUIDField(required=False)
    instance_id = serializers.CharField(max_length=128, required=False)

    def validate(self, attrs):
        if bool(attrs.get('key')) == bool(attrs.get('account_id')):
            raise serializers.ValidationError(_('Provide exactly one of key or account_id.'))
        return attrs


class AuthorizedAccountsSerializer(serializers.Serializer):
    instance_id = serializers.CharField(max_length=128, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=500, default=200)
    offset = serializers.IntegerField(min_value=0, default=0)
    search = serializers.CharField(max_length=128, required=False, allow_blank=True)


class CredentialStateSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64)
    revision = serializers.IntegerField(min_value=1)
    account_id = serializers.UUIDField()


class CredentialConfirmSerializer(CredentialStateSerializer):
    instance_id = serializers.CharField(max_length=128, required=False)


class CredentialAgentRegisterSerializer(serializers.Serializer):
    token = serializers.CharField()
    instance_id = serializers.CharField(max_length=128)
    name = serializers.CharField(max_length=128, required=False, allow_blank=True)
    client_version = serializers.CharField(max_length=32)
    protocol_version = serializers.IntegerField(min_value=1)
    config_schema_version = serializers.IntegerField(min_value=1)


class CredentialRevisionSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64)
    revision = serializers.IntegerField(min_value=0)


class CredentialDeliveryScopeSerializer(serializers.Serializer):
    keys = serializers.ListField(child=serializers.CharField(max_length=128), max_length=200)
    account_ids = serializers.ListField(child=serializers.UUIDField(), max_length=200)

    def validate(self, attrs):
        keys = attrs['keys']
        accounts = [str(value) for value in attrs['account_ids']]
        if len(keys) != len(set(keys)) or len(accounts) != len(set(accounts)):
            raise serializers.ValidationError(_('Duplicate delivery selectors are not allowed.'))
        return {'keys': sorted(keys), 'account_ids': sorted(accounts)}


class CredentialAgentSyncSerializer(serializers.Serializer):
    restart_supported = serializers.BooleanField(required=False, default=False)
    instance_id = serializers.CharField(max_length=128, required=False)
    config_digest = serializers.CharField(max_length=64, required=False, allow_blank=True)
    credentials = CredentialRevisionSerializer(many=True, required=False, default=list)
    delivered_credentials = CredentialRevisionSerializer(many=True, required=False, default=list)
    delivery_scope = CredentialDeliveryScopeSerializer(required=False, allow_null=True)
    sync_status = serializers.ChoiceField(
        choices=['', 'success', 'error'], required=False, default='', allow_blank=True,
    )
    sync_error = serializers.CharField(max_length=128, required=False, default='', allow_blank=True)


class CredentialAccessWizardSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=CredentialClientInstance.Type.choices)
    sdk_language = serializers.ChoiceField(
        choices=[item['value'] for item in sdk_languages()], default='python',
    )
    app_user = serializers.CharField(max_length=128, required=False, default='', allow_blank=True)
    install_path = serializers.CharField(max_length=256, required=False, default='/opt/jumpserver-pam')
    delivery_mode = serializers.ChoiceField(
        choices=DELIVERY_MODES, default='json',
    )
    systemd_unit = serializers.CharField(max_length=128, required=False, default='', allow_blank=True)
    systemd_action = serializers.ChoiceField(
        choices=SYSTEMD_ACTIONS, default='restart',
    )

    def validate(self, attrs):
        application = self.context['application']
        if not application.is_active:
            raise serializers.ValidationError(_('The application is disabled.'))
        if attrs['type'] == CredentialClientInstance.Type.agent and not attrs['app_user']:
            raise serializers.ValidationError({'app_user': _('This field is required for Agent access.')})
        path = attrs['install_path']
        if not path.startswith('/') or path == '/' or any(char in path for char in '\n\r\x00'):
            raise serializers.ValidationError({'install_path': _('Enter an absolute installation directory.')})
        unit = attrs['systemd_unit'].strip()
        if attrs['type'] == 'agent' and attrs['delivery_mode'] == 'environment':
            if not SYSTEMD_UNIT.fullmatch(unit):
                raise serializers.ValidationError({'systemd_unit': _('Enter one systemd .service unit name.')})
            attrs['systemd_unit'] = unit
        else:
            attrs['systemd_unit'] = ''
        return attrs
