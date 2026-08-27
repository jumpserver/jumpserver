from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from accounts.const import (
    CredentialIssueStatus, CredentialLeaseStatus,
    CredentialPolicyMode, CredentialPolicyStatus, SecretType, Source,
)
from accounts.credentials import CredentialError, CredentialPolicyService
from accounts.models import (
    Account, AccountTemplate, CredentialIssueRequest, CredentialLease,
    CredentialPolicy, CredentialPolicyVersion, IntegrationApplication,
)
from common.serializers.fields import LabeledChoiceField, ObjectRelatedField
from orgs.mixins.serializers import BulkOrgResourceModelSerializer
from .account import AccountAssetSerializer
from .template import PasswordRulesSerializer


class CredentialPolicySerializer(BulkOrgResourceModelSerializer):
    application = ObjectRelatedField(
        queryset=IntegrationApplication.objects,
        attrs=('id', 'name'), label=_('Application'),
    )
    mode = LabeledChoiceField(
        choices=CredentialPolicyMode.choices, label=_('Mode'),
    )
    status = LabeledChoiceField(
        choices=CredentialPolicyStatus.choices, read_only=True,
        label=_('Status'),
    )
    asset = AccountAssetSerializer(label=_('Asset'))
    account = ObjectRelatedField(
        queryset=Account.objects, required=False, allow_null=True,
        attrs=('id', 'name', 'username'), label=_('Account'),
    )
    account_template = ObjectRelatedField(
        queryset=AccountTemplate.objects, required=False, allow_null=True,
        attrs=('id', 'name', 'username'), label=_('Account template'),
    )
    management_account = ObjectRelatedField(
        queryset=Account.objects, required=False, allow_null=True,
        attrs=('id', 'name', 'username'), label=_('Management account'),
    )
    rotation_period = serializers.IntegerField(
        source='interval', required=False, allow_null=True,
        min_value=60, label=_('Rotation period'),
    )
    password_rules = PasswordRulesSerializer(
        required=False, label=_('Password rules'),
    )
    next_rotation_at = serializers.SerializerMethodField(
        label=_('Next rotation at'),
    )
    last_execution = ObjectRelatedField(
        read_only=True, attrs=('id', 'status'), label=_('Last execution'),
    )
    last_task_id = serializers.SerializerMethodField(label=_('Task ID'))

    class Meta:
        model = CredentialPolicy
        fields = [
            'id', 'name', 'application', 'mode', 'status',
            'asset', 'account', 'account_template', 'management_account',
            'rotation_period', 'password_rules',
            'username_template', 'platform_params',
            'default_ttl', 'max_ttl', 'max_active_leases',
            'current_version', 'date_last_rotated', 'next_rotation_at',
            'last_execution', 'last_task_id', 'operation_task_id', 'last_error',
            'created_by', 'date_created', 'date_updated', 'comment',
        ]
        read_only_fields = [
            'status', 'current_version', 'date_last_rotated',
            'last_execution', 'operation_task_id', 'last_error',
            'created_by', 'date_created',
        ]
        extra_kwargs = {
            'name': {'label': _('Name')},
            'username_template': {'label': _('Username template')},
            'platform_params': {'label': _('Platform parameters')},
            'default_ttl': {
                'label': _('Default TTL'), 'min_value': 60,
            },
            'max_ttl': {
                'label': _('Maximum TTL'), 'min_value': 60,
            },
            'max_active_leases': {
                'label': _('Maximum active leases'), 'min_value': 1,
            },
        }

    @staticmethod
    def get_next_rotation_at(instance):
        if instance.mode != CredentialPolicyMode.static:
            return None
        try:
            return instance.get_next_run_time()
        except (AttributeError, ValueError):
            return None

    @staticmethod
    def get_last_task_id(instance):
        execution = instance.last_execution
        if not execution:
            return ''
        return str((execution.snapshot or {}).get('celery_task_id') or '')

    @staticmethod
    def _validate_capability(asset, mode):
        automation = getattr(asset.platform, 'automation', None)
        if not automation or not automation.ansible_enabled:
            raise serializers.ValidationError({
                'asset': _('Ansible automation is not enabled for this asset'),
            })
        required = (
            ('change_secret_enabled', 'change_secret_method')
            if mode == CredentialPolicyMode.static
            else (
                'push_account_enabled', 'push_account_method',
                'remove_account_enabled', 'remove_account_method',
            )
        )
        missing = [name for name in required if not getattr(automation, name, None)]
        if missing:
            raise serializers.ValidationError({
                'asset': _('The asset platform does not support this policy mode'),
            })

    def validate(self, attrs):
        attrs = super().validate(attrs)
        instance = self.instance

        def value(name, default=None):
            if name in attrs:
                return attrs[name]
            return getattr(instance, name, default) if instance else default

        application = value('application')
        mode = value('mode')
        asset = value('asset')
        account = value('account')
        template = value('account_template')
        management = value('management_account')
        if not isinstance(value('platform_params', {}), dict):
            raise serializers.ValidationError({
                'platform_params': _('Platform parameters must be an object'),
            })

        if instance:
            immutable = (
                'application', 'mode', 'asset', 'account', 'account_template',
            )
            changed = [
                name for name in immutable
                if name in attrs
                and getattr(getattr(instance, name), 'id', getattr(instance, name))
                != getattr(attrs[name], 'id', attrs[name])
            ]
            if changed:
                raise serializers.ValidationError(
                    _('Policy bindings cannot be changed after creation')
                )

        if not application or not application.is_active:
            raise serializers.ValidationError({
                'application': _('Application is not active'),
            })
        if not asset or not asset.is_active:
            raise serializers.ValidationError({'asset': _('Asset is not active')})

        org_ids = {application.org_id, asset.org_id}
        org_ids.update(
            obj.org_id for obj in (account, template, management) if obj
        )
        if len(org_ids) != 1:
            raise serializers.ValidationError(
                _('Policy resources must belong to the same organization')
            )

        if not management:
            management = asset.all_valid_accounts.filter(
                privileged=True,
            ).order_by('-date_updated').first()
            if not management:
                raise serializers.ValidationError({
                    'management_account': _('A management account is required'),
                })
            attrs['management_account'] = management
        elif not asset.all_valid_accounts.filter(id=management.id).exists():
            raise serializers.ValidationError({
                'management_account': _('Management account does not belong to the asset'),
            })
        if management.source == Source.CREDENTIAL_LEASE:
            raise serializers.ValidationError({
                'management_account': _(
                    'A temporary credential account cannot manage a policy'
                ),
            })
        try:
            management_has_secret = management.has_secret
        except Exception:
            management_has_secret = False
        if not management_has_secret:
            raise serializers.ValidationError({
                'management_account': _(
                    'Management account must have a usable secret'
                ),
            })

        self._validate_capability(asset, mode)
        if mode == CredentialPolicyMode.dynamic:
            try:
                CredentialPolicyService.validate_dynamic_automation(
                    asset, template.secret_type if template else None,
                )
            except CredentialError as error:
                raise serializers.ValidationError({'asset': error.detail})
        if mode == CredentialPolicyMode.static:
            if not account or template:
                raise serializers.ValidationError(
                    _('Rotating account policy requires one account and no template')
                )
            if not asset.all_valid_accounts.filter(id=account.id).exists():
                raise serializers.ValidationError({
                    'account': _('Account does not belong to the asset'),
                })
            if account.source == Source.CREDENTIAL_LEASE:
                raise serializers.ValidationError({
                    'account': _(
                        'A temporary credential account cannot be rotated by a policy'
                    ),
                })
            try:
                account_has_secret = account.has_secret
            except Exception:
                account_has_secret = False
            if not account.secret_reset or not account_has_secret:
                raise serializers.ValidationError({
                    'account': _(
                        'Rotating account must allow secret reset and have a current secret'
                    ),
                })
            duplicate = CredentialPolicy.objects.filter(account=account)
            if instance:
                duplicate = duplicate.exclude(id=instance.id)
            if duplicate.exists():
                raise serializers.ValidationError({
                    'account': _('Account already belongs to a credential policy'),
                })
            if account.secret_type not in (SecretType.PASSWORD, SecretType.SSH_KEY):
                raise serializers.ValidationError({
                    'account': _('Account secret type cannot be rotated'),
                })
            if value('interval', 86400) is None:
                raise serializers.ValidationError({
                    'rotation_period': _('Rotation period is required'),
                })
            attrs.update({
                'account_template': None,
                'default_ttl': None,
                'max_ttl': None,
                'max_active_leases': None,
            })
        else:
            if account or not template:
                raise serializers.ValidationError(
                    _('Temporary account policy requires one template and no account')
                )
            if template.secret_type not in (SecretType.PASSWORD, SecretType.SSH_KEY):
                raise serializers.ValidationError({
                    'account_template': _('Template secret type cannot be issued'),
                })
            if template.platforms.exists() and not template.platforms.filter(
                id=asset.platform_id,
            ).exists():
                raise serializers.ValidationError({
                    'account_template': _('Template does not support the asset platform'),
                })
            default_ttl = value('default_ttl', 3600)
            max_ttl = value('max_ttl', 86400)
            if not default_ttl or not max_ttl or default_ttl > max_ttl:
                raise serializers.ValidationError({
                    'max_ttl': _('Maximum TTL must not be shorter than default TTL'),
                })
            if not value('max_active_leases', 10):
                raise serializers.ValidationError({
                    'max_active_leases': _('Maximum active leases is required'),
                })
            try:
                CredentialPolicyService.validate_username_template(
                    value(
                        'username_template',
                        'jms_{application}_{policy}_{random}',
                    ),
                )
            except CredentialError as error:
                raise serializers.ValidationError({
                    'username_template': error.detail,
                })
            attrs.update({'account': None, 'interval': None})
            if 'platform_params' not in attrs and not instance:
                attrs['platform_params'] = (
                    template.push_params
                    if isinstance(template.push_params, dict)
                    else {}
                )
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        is_static = validated_data['mode'] == CredentialPolicyMode.static
        validated_data['current_version'] = 1 if is_static else 0
        instance = super().create(validated_data)
        if is_static:
            CredentialPolicyVersion.objects.create(
                policy=instance,
                version=1,
                account=instance.account,
                account_version=instance.account.version,
                org_id=instance.org_id,
            )
        return instance


class CredentialPolicyVersionSerializer(BulkOrgResourceModelSerializer):
    policy = ObjectRelatedField(read_only=True, attrs=('id', 'name'))
    account = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'username'),
    )
    change_secret_record = ObjectRelatedField(
        read_only=True, attrs=('id', 'status'),
    )

    class Meta:
        model = CredentialPolicyVersion
        fields = [
            'id', 'policy', 'version', 'account', 'account_version',
            'change_secret_record', 'date_created', 'comment',
        ]
        read_only_fields = fields


class CredentialIssueRequestSerializer(BulkOrgResourceModelSerializer):
    policy = ObjectRelatedField(read_only=True, attrs=('id', 'name'))
    status = LabeledChoiceField(
        choices=CredentialIssueStatus.choices, read_only=True,
    )
    lease = ObjectRelatedField(read_only=True, attrs=('id', 'status'))
    execution = ObjectRelatedField(read_only=True, attrs=('id', 'status'))
    cleanup_execution = ObjectRelatedField(
        read_only=True, attrs=('id', 'status'),
    )

    class Meta:
        model = CredentialIssueRequest
        fields = [
            'id', 'policy', 'status', 'username', 'lease', 'execution',
            'cleanup_execution',
            'deadline', 'replay_until', 'date_completed', 'remote_addr',
            'error_code', 'error', 'date_created',
        ]
        read_only_fields = fields


class CredentialLeaseSerializer(BulkOrgResourceModelSerializer):
    policy = ObjectRelatedField(read_only=True, attrs=('id', 'name'))
    account = ObjectRelatedField(
        read_only=True, attrs=('id', 'name', 'username'),
    )
    status = LabeledChoiceField(
        choices=CredentialLeaseStatus.choices, read_only=True,
    )
    issue_execution = ObjectRelatedField(
        read_only=True, attrs=('id', 'status'),
    )
    revoke_execution = ObjectRelatedField(
        read_only=True, attrs=('id', 'status'),
    )
    revoke_task_id = serializers.SerializerMethodField(label=_('Task ID'))
    ttl = serializers.SerializerMethodField(label=_('TTL'))

    class Meta:
        model = CredentialLease
        fields = [
            'id', 'policy', 'account', 'username', 'status', 'ttl',
            'renewable', 'date_expires', 'date_max_expires',
            'date_last_renewed', 'date_revoked', 'renew_count',
            'revoke_reason', 'revoke_succeeded', 'revoke_error',
            'issue_execution', 'revoke_execution', 'revoke_task_id',
            'date_created',
        ]
        read_only_fields = fields

    @staticmethod
    def get_ttl(instance):
        return max(0, int((instance.date_expires - timezone.now()).total_seconds()))

    @staticmethod
    def get_revoke_task_id(instance):
        execution = instance.revoke_execution
        if not execution:
            return ''
        return str((execution.snapshot or {}).get('celery_task_id') or '')


class CredentialLeaseRenewSerializer(serializers.Serializer):
    increment = serializers.IntegerField(
        required=False, allow_null=True, min_value=1,
        max_value=2_147_483_647,
        label=_('Renew increment'),
    )
