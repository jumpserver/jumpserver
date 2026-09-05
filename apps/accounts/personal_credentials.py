from uuid import UUID

from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import APIException, NotFound, PermissionDenied

from accounts.const import AliasAccount, SecretType
from accounts.utils import validate_account_username, validate_ssh_key
from assets.const import AllTypes, Connectivity, Protocol
from assets.models import Asset
from orgs.utils import tmp_to_org
from perms.const import ActionChoices
from perms.utils import PermAssetDetailUtil

from .models import PersonalAssetCredential


PERSONAL_CREDENTIAL_SECRET_TYPES = frozenset(
    value for value, __ in SecretType.choices
    if value != SecretType.SSH_CERTIFICATE
)
PERSONAL_CREDENTIAL_SECRET_CHOICES = tuple(
    choice for choice in SecretType.choices
    if choice[0] in PERSONAL_CREDENTIAL_SECRET_TYPES
)
PERSONAL_CREDENTIAL_SAFE_VERIFY_METHODS = frozenset({
    'verify_account_postgresql',
    'verify_account_oracle',
    'verify_account_mongodb',
    'verify_account_mysql',
    'verify_account_sqlserver',
    'verify_account_posix',
    'verify_account_windows',
    'verify_account_by_rdp',
    'verify_account_by_ssh',
})


def get_personal_credential_failure_reason(error):
    codes = error.get_codes() if hasattr(error, 'get_codes') else None
    flattened = []

    def collect(value):
        if isinstance(value, dict):
            for child in value.values():
                collect(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                collect(child)
        elif isinstance(value, str) and value not in flattened:
            flattened.append(value)

    collect(codes)
    if not flattened:
        flattened.append(error.__class__.__name__)
    return ','.join(flattened[:8])[:240]


def record_personal_credential_audit(
        *, operation, result, user, asset=None, credential=None,
        credential_id=None, username='', secret_type='', remote_addr=None,
        failure_reason='', org_id=None,
):
    """Record metadata only; a credential secret must never enter the audit log."""
    from audits.const import ActionChoices as AuditActionChoices
    from audits.handler import create_or_update_operate_log

    action_mapper = {
        'create': AuditActionChoices.create,
        'update': AuditActionChoices.update,
        'delete': AuditActionChoices.delete,
        'test': AuditActionChoices.connect,
        'use': AuditActionChoices.connect,
    }

    def safe_scalar(value, max_length=240):
        if not isinstance(value, (str, int, float, bool, UUID)):
            return ''
        value = ''.join(
            char for char in str(value)
            if char.isprintable() and char not in '\r\n'
        )
        return value[:max_length]

    action = action_mapper.get(operation, AuditActionChoices.view)
    if credential:
        credential_id = credential.id
        username = credential.username
        secret_type = credential.secret_type
        asset = credential.asset
    if org_id is None and asset is not None:
        org_id = asset.org_id
    credential_id = safe_scalar(credential_id, 36)
    username = safe_scalar(username, 128)
    secret_type = safe_scalar(secret_type, 16)
    operation = safe_scalar(operation, 16)
    result = safe_scalar(result, 16)
    failure_reason = safe_scalar(failure_reason)
    asset_display = safe_scalar(str(asset), 128) if asset is not None else ''
    display = username or credential_id or str(_('Personal asset credential'))
    details = {
        str(_('Credential ID')): {
            'name': 'id',
            'value': credential_id,
        },
        str(_('Asset')): {
            'name': 'asset',
            'value': asset_display,
        },
        str(_('Username')): {
            'name': 'username',
            'value': username,
        },
        str(_('Secret type')): {
            'name': 'secret_type',
            'value': secret_type,
        },
        str(_('Operation')): {
            'name': 'operation',
            'value': operation,
        },
        str(_('Result')): {
            'name': 'result',
            'value': result,
        },
        str(_('Failure reason')): {
            'name': 'failure_reason',
            'value': failure_reason,
        },
    }
    create_or_update_operate_log(
        action,
        _('Personal asset credential'),
        resource=credential,
        resource_display=display,
        force=True,
        after=details,
        object_name='PersonalAssetCredential',
        user=user,
        org_id=str(org_id) if org_id is not None else None,
        remote_addr=remote_addr,
        resource_id=credential_id,
    )


class PersonalCredentialVersionConflict(APIException):
    status_code = 409
    default_detail = _('The personal credential has been updated. Please refresh and try again.')
    default_code = 'personal_credential_version_conflict'


def get_personal_credential_permission_context(user, asset, protocol):
    if not user or not user.is_valid:
        raise PermissionDenied(_('Invalid user'), code='invalid_user')
    if not asset or not asset.is_active:
        raise PermissionDenied(_('Asset is inactive'), code='asset_inactive')

    asset_protocol_exists = asset.protocols.filter(name=protocol).exists()
    platform_protocol = asset.platform.protocols.filter(name=protocol).first()
    if not asset_protocol_exists or not platform_protocol:
        raise serializers.ValidationError({'protocol': _('Protocol is not supported by this asset')})

    try:
        account = PermAssetDetailUtil(user, asset).validate_permission(
            AliasAccount.INPUT, protocol
        )
    except Asset.DoesNotExist:
        account = None
    if not account or not ActionChoices.contains(account.actions, ActionChoices.connect):
        raise PermissionDenied(
            _('You do not have manual account permission for this asset'),
            code='manual_account_permission_denied',
        )
    if account.date_expired < timezone.now():
        raise PermissionDenied(_('Permission expired'), code='permission_expired')
    return platform_protocol, account


def validate_personal_credential_test_acl(
        user, asset, permission_account, username, remote_addr,
):
    """Allow a direct verification probe only when login ACL needs no flow."""
    from acls.models import LoginAssetACL

    acls = LoginAssetACL.filter_queryset(
        user=user,
        asset=asset,
        account=permission_account,
        account_username=username,
    )
    acl = LoginAssetACL.get_match_rule_acls(user, remote_addr, acls)
    if not acl or acl.is_action(acl.ActionChoices.accept):
        return
    raise PermissionDenied(
        _(
            'Credential verification is unavailable because the asset login '
            'ACL requires an additional action'
        ),
        code='personal_credential_test_acl_denied',
    )


def get_personal_credential_verification_method(asset):
    auto_config = asset.auto_config
    method_id = auto_config.get('verify_account_method')
    if not (
        auto_config.get('ansible_enabled')
        and auto_config.get('verify_account_enabled')
        and method_id
    ):
        raise serializers.ValidationError(
            _('Credential verification is not supported by this asset'),
            code='credential_verification_not_supported',
        )

    methods = AllTypes.get_automation_methods()
    method = next((item for item in methods if item.get('id') == method_id), None)
    if method is None:
        methods = AllTypes.reload_automation_methods()
        method = next((item for item in methods if item.get('id') == method_id), None)
    if not method or method.get('method') != 'verify_account':
        raise serializers.ValidationError(
            _('Credential verification method is unavailable'),
            code='credential_verification_method_unavailable',
        )
    if method_id not in PERSONAL_CREDENTIAL_SAFE_VERIFY_METHODS:
        raise serializers.ValidationError(
            _(
                'Personal credential verification does not allow custom '
                'automation methods'
            ),
            code='credential_verification_method_not_safe',
        )
    return method


def validate_personal_credential_verification_protocol(asset, protocol):
    """Bind a personal probe to the protocol the configured runner will use."""
    method = get_personal_credential_verification_method(asset)
    protocols = list(asset.protocols.all())
    ansible_config = asset.auto_config.get('ansible_config') or {}
    ansible_connection = ansible_config.get('ansible_connection')
    protocol_priority = {'ssh': 10, 'winrm': 9, ansible_connection: 1}
    method_protocol = method.get('protocol')
    if method_protocol:
        protocol_priority[method_protocol] = 0
    protocols.sort(key=lambda item: protocol_priority.get(item.name, 999))
    actual_protocol = protocols[0].name if protocols else None
    uses_compatible_runner = (
        actual_protocol == protocol
        or (
            protocol == Protocol.sftp
            and actual_protocol == Protocol.ssh
        )
    )
    if not uses_compatible_runner:
        raise serializers.ValidationError(
            {
                'protocol': _(
                    'The configured credential verification method does not '
                    'support this protocol'
                )
            },
            code='credential_verification_protocol_mismatch',
        )
    return method


def validate_personal_credential_secret_type(
        platform_protocol, secret_type, field_name='secret_type',
):
    if (
        secret_type not in PERSONAL_CREDENTIAL_SECRET_TYPES
        or secret_type not in platform_protocol.secret_types
    ):
        raise serializers.ValidationError({
            field_name: _('Secret type is not supported by this protocol')
        })


def get_personal_credential_for_use(
        user, asset, protocol, credential_id, version=None, include_secret=False,
        permission_context=None,
):
    if permission_context is None:
        permission_context = get_personal_credential_permission_context(
            user, asset, protocol
        )
    platform_protocol, __ = permission_context
    with tmp_to_org(asset.org_id):
        queryset = PersonalAssetCredential.objects.filter(
            id=credential_id,
            owner=user,
            asset=asset,
            protocol=protocol,
            is_active=True,
        )
        if version is not None:
            queryset = queryset.filter(version=version)
        if not include_secret:
            queryset = queryset.defer('_secret')
        credential = queryset.first()
    if not credential:
        raise NotFound(
            _('Personal credential not found'),
            code='personal_credential_not_found',
        )
    validate_personal_credential_secret_type(
        platform_protocol, credential.secret_type
    )
    return credential


@transaction.atomic
def save_personal_credential(
        *, user, asset, protocol, username, secret, secret_type,
        credential_id=None, version=None, permission_context=None,
):
    if permission_context is None:
        permission_context = get_personal_credential_permission_context(
            user, asset, protocol
        )
    platform_protocol, __ = permission_context
    username = validate_account_username(username)
    if not username:
        raise serializers.ValidationError({'input_username': _('This field is required.')})
    if not secret:
        raise serializers.ValidationError({'input_secret': _('This field is required.')})
    validate_personal_credential_secret_type(
        platform_protocol, secret_type, field_name='input_secret_type'
    )
    if secret_type == 'ssh_key':
        secret = validate_ssh_key(secret)
    with tmp_to_org(asset.org_id):
        if credential_id:
            credential = PersonalAssetCredential.objects.select_for_update().filter(
                id=credential_id, owner=user, asset=asset, protocol=protocol,
            ).first()
            if not credential:
                raise NotFound(
                    _('Personal credential not found'),
                    code='personal_credential_not_found',
                )
            if version is None or credential.version != version:
                is_idempotent_retry = (
                    version is not None
                    and credential.version == version + 1
                    and credential.username == username
                    and credential.secret == secret
                    and credential.secret_type == secret_type
                    and credential.is_active
                )
                if is_idempotent_retry:
                    return credential
                raise PersonalCredentialVersionConflict()
            credential.username = username
            credential.secret = secret
            credential.secret_type = secret_type
            credential.is_active = True
            credential.version += 1
            credential.connectivity = Connectivity.UNKNOWN
            credential.date_verified = None
            credential.updated_by = str(user)
            try:
                credential.save()
            except IntegrityError as error:
                raise serializers.ValidationError({
                    'input_username': _(
                        'A personal credential with these fields already exists'
                    )
                }) from error
            return credential

        try:
            return PersonalAssetCredential.objects.create(
                owner=user,
                asset=asset,
                username=username,
                secret=secret,
                secret_type=secret_type,
                protocol=protocol,
                is_active=True,
                created_by=str(user),
                updated_by=str(user),
            )
        except IntegrityError as error:
            raise serializers.ValidationError({
                'input_username': _('A personal credential with these fields already exists')
            }) from error
