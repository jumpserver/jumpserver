import json
from ipaddress import ip_address
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from accounts.const import AliasAccount, SecretType
from accounts.personal_credentials import (
    get_personal_credential_failure_reason, get_personal_credential_for_use,
    get_personal_credential_permission_context, record_personal_credential_audit,
    save_personal_credential, validate_personal_credential_secret_type,
)
from accounts.utils import validate_account_username, validate_ssh_key
from acls.models import ConnectMethodACL
from acls.notifications import AssetLoginReminderMsg
from common.exceptions import JMSException
from common.utils import get_logger, get_request_ip_or_data, random_string
from common.utils.django import get_request_os
from common.utils.http import is_false, is_true
from orgs.utils import tmp_to_org, tmp_to_root_org
from terminal.connect_methods import ConnectMethodUtil, WebMethod
from users.models import Preference
from authentication.const import ConnectionTokenType
from authentication.mixins import AuthFaceMixin
from authentication.models import AdminConnectionToken, ConnectionToken
from authentication.utils import get_effective_connect_options
from .ssh_certificate import sign_connection_token_ssh_certificate

logger = get_logger(__name__)


def record_connection_token_credential_audit(token, *, result, error=None, request=None):
    """Record personal credential use using token metadata, without reading its secret."""
    if not token.personal_credential_id:
        return

    failure_reason = ''
    if error is not None:
        failure_reason = (
            get_personal_credential_failure_reason(error)
            if isinstance(error, APIException)
            else error.__class__.__name__
        )
    record_personal_credential_audit(
        operation='use',
        result=result,
        failure_reason=failure_reason,
        user=token.user,
        asset=token.asset,
        credential_id=token.personal_credential_id,
        username=token.input_username,
        secret_type=token.input_secret_type,
        remote_addr=(
            get_request_ip_or_data(request)
            if request is not None else token.remote_addr
        ),
        org_id=token.org_id,
    )


@transaction.atomic
def get_connection_token_secret(token, serializer_factory, *, expire_now=True, public_key=''):
    """Return credentials using the shared token validation and consumption rules."""
    # Serialize credential release with cancellation and competing consumers;
    # discard properties cached on the model before the lock was acquired.
    token = type(token).objects.select_for_update().get(pk=token.pk)
    requested_expire_now = expire_now
    try:
        # Only personal tokens load a version-bound credential during validation.
        # account_object reuses it on this request-local token instance.
        token.is_valid(include_personal_secret=True)
        account = token.account_object
    except Exception as error:
        record_connection_token_credential_audit(token, result='failed', error=error)
        raise
    if account and account.secret_type == SecretType.SSH_CERTIFICATE:
        certificate = sign_connection_token_ssh_certificate(token, public_key)
        # The certificate is public material, but returning it through the
        # existing account credential field keeps the component contract
        # compact. Koko pairs it with the private key generated in memory.
        account.secret = certificate['signed_key']
        token.ssh_certificate = {
            key: value for key, value in certificate.items()
            if key != 'signed_key'
        }

    serializer = serializer_factory(instance=token)

    expire_now = requested_expire_now
    asset_type = token.asset.type
    # 设置默认值
    if asset_type in ['k8s', 'kubernetes']:
        expire_now = False

    if token.is_reusable and settings.CONNECTION_TOKEN_REUSABLE:
        logger.debug('Token is reusable, not expire now')
    elif is_false(expire_now):
        logger.debug('API specified, do not expire now')
    else:
        token.expire()

    # expire_now=false still returns the secret. Audit every disclosure,
    # while distinguishing Koko's inspection phase from final consumption.
    record_connection_token_credential_audit(
        token,
        result='inspected' if is_false(requested_expire_now) else 'success',
    )

    ConnectionToken.objects.filter(pk=token.pk).update(date_last_used=timezone.now())

    return serializer.data


class ConnectionTokenService(AuthFaceMixin):
    """Shared connection creation, permission checks and ACL initialization.

    The API inherits these hooks for compatibility with its normal, component
    and administrator variants. Non-HTTP callers supply a request context and
    a validated serializer without constructing an API view.
    """
    input_username = ''
    need_face_verify = False
    face_monitor_token = ''
    personal_credential_audit_context = None
    personal_credential_saved = None
    verified_remote_addr = None

    @classmethod
    def for_request(cls, request, *, verified_remote_addr=None):
        service = cls()
        service.request = request
        # Only internal callers with an authenticated component context supply
        # this address; ordinary API requests still use the existing IP policy.
        if verified_remote_addr:
            try:
                verified_remote_addr = str(ip_address(verified_remote_addr))
            except ValueError:
                raise ValidationError({'remote_addr': _('Invalid IP address')})
        service.verified_remote_addr = verified_remote_addr
        return service

    def get_remote_addr(self):
        if self.verified_remote_addr is not None:
            return self.verified_remote_addr
        return get_request_ip_or_data(self.request)

    def get_user(self, serializer):
        return self.request.user

    @transaction.atomic
    def create_token(self, serializer):
        self.validate_serializer(serializer)
        if self.verified_remote_addr is not None:
            serializer.context['verified_remote_addr'] = self.verified_remote_addr
        return serializer.save()

    def _insert_connect_options(self, data, user):
        connect_options = data.pop('connect_options', {})
        default_name_opts = {
            'file_name_conflict_resolution': settings.LUNA_DEFAULT_FILE_NAME_CONFLICT_RESOLUTION,
            'terminal_theme_name': settings.LUNA_DEFAULT_TERMINAL_THEME_NAME,
        }
        backspace_preference_name = 'is_backspace_as_ctrl_h'
        resolution_preference_name = 'rdp_resolution'
        rdp_client_option_preference_name = 'rdp_client_option'
        preferences_query = Preference.objects.filter(
            user=user, category='luna',
            name__in=(
                *default_name_opts.keys(),
                backspace_preference_name,
                resolution_preference_name,
                rdp_client_option_preference_name,
                'printers_redirect',
            )
        ).values_list('name', 'value')
        preferences = dict(preferences_query)
        for name in default_name_opts.keys():
            value = preferences.get(name, default_name_opts[name])
            connect_options[name] = value

        # Applet connections can also use RDP regardless of the asset protocol.
        printers_redirect = connect_options.get('printers_redirect')
        if printers_redirect is None:
            printers_redirect = preferences.get('printers_redirect', False)
        if isinstance(printers_redirect, str):
            printers_redirect = printers_redirect.lower()
        connect_options['printers_redirect'] = is_true(printers_redirect)

        # The advanced option submitted by Luna takes precedence.  When it is
        # absent, use the personal preference as the connection default.
        if 'backspaceAsCtrlH' not in connect_options:
            # Koko consumes this option using camelCase. Preferences are stored
            # in a TextField, so convert the value back to a real boolean.
            backspace_as_ctrl_h = preferences.get(
                backspace_preference_name, settings.LUNA_DEFAULT_IS_BACKSPACE_AS_CTRL_H
            )
            connect_options['backspaceAsCtrlH'] = is_true(backspace_as_ctrl_h)

        if data.get('protocol') == 'rdp':
            if 'resolution' not in connect_options:
                connect_options['resolution'] = preferences.get(
                    resolution_preference_name, settings.LUNA_DEFAULT_RDP_RESOLUTION
                )

            if 'remote_microphone' not in connect_options:
                rdp_client_options = preferences.get(
                    rdp_client_option_preference_name,
                    settings.LUNA_DEFAULT_RDP_CLIENT_OPTION,
                )
                if isinstance(rdp_client_options, str):
                    try:
                        rdp_client_options = json.loads(rdp_client_options)
                    except json.JSONDecodeError:
                        rdp_client_options = settings.LUNA_DEFAULT_RDP_CLIENT_OPTION
                if not isinstance(rdp_client_options, (list, set, tuple)):
                    rdp_client_options = settings.LUNA_DEFAULT_RDP_CLIENT_OPTION
                connect_options['remote_microphone'] = 'remote_microphone' in rdp_client_options
        connect_options['lang'] = getattr(user, 'lang') or settings.LANGUAGE_CODE
        data['connect_options'] = connect_options

    @staticmethod
    def get_input_username(data):
        input_username = data.get('input_username', '')
        if input_username:
            return input_username

        account = data.get('account', '')
        if account == '@USER':
            input_username = str(data.get('user', ''))
        elif account == '@INPUT':
            input_username = '@INPUT'
        else:
            input_username = account
        return input_username

    def validate_serializer(self, serializer):
        data = serializer.validated_data
        user = self.get_user(serializer)
        self._insert_connect_options(data, user)
        asset = data.get('asset')
        account_name = data.get('account')
        protocol = data.get('protocol')
        connect_method = data.get('connect_method')
        save_credential = data.pop('save_personal_credential', False)
        credential_version = data.pop('personal_credential_version', None)
        credential_id = data.get('personal_credential_id')
        personal_permission_context = None
        personal_permission_account = None
        if credential_id or save_credential:
            self.personal_credential_audit_context = {
                'operation': (
                    'update' if credential_id and save_credential
                    else 'create' if save_credential
                    else 'use'
                ),
                'asset': asset,
                'credential_id': credential_id,
                'username': data.get('input_username', ''),
                'secret_type': data.get('input_secret_type', ''),
            }
        data['connect_options'] = get_effective_connect_options(
            data['connect_options'], protocol, asset
        )

        if credential_id or save_credential:
            if user != self.request.user:
                raise PermissionDenied(_(
                    'Personal credentials can only be managed by their owner'
                ))
            personal_permission_context = get_personal_credential_permission_context(
                user, asset, protocol, account_alias=account_name,
            )
            platform_protocol, personal_permission_account = personal_permission_context
            if save_credential and account_name != AliasAccount.INPUT:
                # Same-name and hosted accounts fix the username.
                data['input_username'] = personal_permission_account.full_username

        if save_credential:
            if not data.get('input_username'):
                raise ValidationError({'input_username': _('This field is required.')})
            if not data.get('input_secret'):
                raise ValidationError({'input_secret': _('This field is required.')})
            input_secret_type = (
                data.get('input_secret_type') or SecretType.PASSWORD
            )
            validate_personal_credential_secret_type(
                platform_protocol,
                input_secret_type,
                field_name='input_secret_type',
            )
            if input_secret_type == SecretType.SSH_KEY:
                data['input_secret'] = validate_ssh_key(data['input_secret'])
            if credential_id and credential_version is None:
                raise ValidationError({
                    'personal_credential_version': _('This field is required.')
                })
        if credential_version is not None and not credential_id:
            raise ValidationError({
                'personal_credential_version': _(
                    'A personal credential ID is required when a version is provided'
                )
            })

        if credential_id:
            if not save_credential and (data.get('input_username') or data.get('input_secret')):
                raise ValidationError({
                    'personal_credential_id': _(
                        'Do not submit a username or secret when using a saved credential'
                    )
                })
            credential = get_personal_credential_for_use(
                user, asset, protocol, credential_id,
                # Updates check the submitted version under the write lock,
                # including idempotent retries; use binds the exact version.
                version=None if save_credential else credential_version,
                permission_context=personal_permission_context,
            )
            if not save_credential:
                data['input_username'] = credential.username
                data['input_secret'] = ''
                data['input_secret_type'] = credential.secret_type
                data['personal_credential_version'] = credential.version
                self.personal_credential_audit_context.update({
                    'username': credential.username,
                    'secret_type': credential.secret_type,
                })

        self.input_username = self.get_input_username(data)
        if account_name == AliasAccount.INPUT:
            # Manual account input can reach Luna directly, so validate before ACL/token creation.
            self.input_username = validate_account_username(self.input_username)
            data['input_username'] = self.input_username
        _data = self._validate(
            user, asset, account_name, protocol, connect_method,
            permed_account=personal_permission_account,
        )
        _data['remote_addr'] = self.get_remote_addr()
        data.update(_data)
        if 'push_account' in data.get('acl_context', {}).get('requirements', {}):
            supplied = {
                field: _('Same-name account provisioning uses server-managed credentials.')
                for field in ('input_username', 'input_secret', 'input_secret_type',
                              'personal_credential_id', 'personal_credential_version', 'save_personal_credential')
                if self.request.data.get(field)
            }
            if supplied:
                raise ValidationError(supplied)
            data['input_username'] = ''
            data['input_secret'] = ''
            data['date_expired'] = timezone.now() + timedelta(minutes=15)


        if save_credential:
            credential = save_personal_credential(
                user=user,
                asset=asset,
                protocol=protocol,
                username=self.input_username,
                secret=data.get('input_secret', ''),
                secret_type=data.get('input_secret_type') or SecretType.PASSWORD,
                credential_id=credential_id,
                version=credential_version,
                permission_context=personal_permission_context,
            )
            data['personal_credential_id'] = credential.id
            data['personal_credential_version'] = credential.version
            data['input_username'] = credential.username
            data['input_secret'] = ''
            data['input_secret_type'] = credential.secret_type
            self.personal_credential_audit_context.update({
                'credential_id': credential.id,
                'username': credential.username,
                'secret_type': credential.secret_type,
            })
            self.personal_credential_saved = (
                'update' if credential_id else 'create', credential
            )
        return serializer

    def validate_exchange_token(self, token):
        token.connect_options = get_effective_connect_options(
            token.connect_options, token.protocol, token.asset
        )
        user = token.user
        asset = token.asset
        account_alias = token.account
        self.input_username = token.input_username
        self.face_monitor_token = token.face_monitor_token or ''
        personal_permission_account = None
        if token.personal_credential_id:
            credential, permission_context = (
                token.validate_personal_credential()
            )
            personal_permission_account = permission_context[1]
            self.input_username = credential.username
            token.input_username = credential.username
            token.input_secret = ''
            token.input_secret_type = credential.secret_type
        _data = self._validate(
            user, asset, account_alias, token.protocol, token.connect_method,
            permed_account=personal_permission_account,
        )
        _data['remote_addr'] = self.get_remote_addr()
        for k, v in _data.items():
            setattr(token, k, v)
        return token

    def _validate(
            self, user, asset, account_alias, protocol, connect_method,
            permed_account=None,
    ):
        if not ConnectMethodACL.is_method_allowed(user, asset, connect_method, protocol):
            raise JMSException(
                code='connect_method_rejected',
                detail=_('Connect method is not allowed for this asset')
            )
        data = dict()
        data['org_id'] = asset.org_id
        data['user'] = user
        data['value'] = random_string(16)

        if account_alias == AliasAccount.ANON and asset.category not in ['web', 'custom']:
            raise ValidationError(_('Anonymous account is not supported for this asset'))

        account = permed_account
        if account is None:
            account = self._validate_perm(
                user, asset, account_alias, protocol
            )
        if account.has_secret:
            data['input_secret'] = ''
            data['input_secret_type'] = account.secret_type

        if account_alias != AliasAccount.INPUT and account_alias != AliasAccount.USER:
            data['input_username'] = ''
            if account.has_secret:
                data['input_secret_type'] = ''

        data['acl_context'] = self._validate_acl(user, asset, account, connect_method, protocol)
        data['is_active'] = not data['acl_context'].get('requirements')
        if self.face_monitor_token and data['acl_context'].get('face_online'):
            from authentication.api.face import FaceMonitorContext
            context = FaceMonitorContext.get_or_create_context(self.face_monitor_token, self.request.user.id)
            if str(context.user_id) != str(user.id):
                raise PermissionDenied(_('Face monitoring context belongs to a different user'))
            data['face_monitor_token'] = self.face_monitor_token
        else:
            data['face_monitor_token'] = ''
        return data

    @staticmethod
    def get_permed_account(user, asset, account_alias, protocol):
        return ConnectionToken.get_user_permed_account(user, asset, account_alias, protocol)

    def _validate_perm(self, user, asset, account_alias, protocol, token_type=None):
        get_permed_account = self.get_permed_account
        if token_type == ConnectionTokenType.ADMIN:
            get_permed_account = AdminConnectionToken.get_user_permed_account
        account = get_permed_account(user, asset, account_alias, protocol)
        if not ConnectionToken.has_account_permission(account, protocol):
            msg = _('Account not found')
            raise JMSException(code='perm_account_invalid', detail=msg)
        if account.date_expired < timezone.now():
            msg = _('Permission expired')
            raise JMSException(code='perm_expired', detail=msg)
        return account

    def _record_operate_log(self, acl, asset):
        from audits.handler import create_or_update_operate_log
        with tmp_to_org(asset.org_id):
            after = {
                str(_('Assets')): str(asset),
                str(_('Account')): self.input_username
            }
            object_name = acl._meta.object_name
            resource_type = acl._meta.verbose_name
            create_or_update_operate_log(
                acl.action, resource_type, resource=acl,
                after=after, object_name=object_name
            )

    def _validate_acl(self, user, asset, account, connect_method, protocol):
        from acls.models import LoginAssetACL
        kwargs = {'user': user, 'asset': asset, 'account': account}
        if account.username == AliasAccount.INPUT:
            kwargs['account_username'] = self.input_username
        ip = self.get_remote_addr()
        policy = LoginAssetACL.get_match_rule_acls(user, ip, LoginAssetACL.filter_queryset(**kwargs))
        if not policy:
            return {}
        self._record_operate_log(policy.decision_rule, asset)
        if policy.action == policy.ActionChoices.reject:
            raise JMSException(code='acl_reject', detail=_('ACL action is reject: {}({})').format(policy.name, policy.id))
        username = self.input_username if account.username == AliasAccount.INPUT else account.username
        reviews = policy.pending_reviews(user, asset, username)
        requirements = {}
        for control in ('reason', 'mfa'):
            if policy.enabled(f'{control}_enabled'):
                requirements[control] = 'pending'
        self.need_face_verify = policy.enabled('face_verify_enabled') or policy.enabled('face_online_enabled')
        if self.need_face_verify:
            if user != self.request.user:
                raise JMSException(code='acl_face_verify', detail=_('Use Web Terminal to complete face verification'))
            requirements['face'] = 'pending'
        if reviews:
            requirements['review'] = 'pending'
        if policy.enabled('push_account_enabled') and LoginAssetACL.is_same_account(user, account, username):
            from accounts.provisioning import needs_account_preparation
            if needs_account_preparation(account):
                requirements['push_account'] = 'pending'
        if policy.enabled('face_online_enabled'):
            if connect_method not in [WebMethod.web_cli, WebMethod.web_gui]:
                raise JMSException(code='acl_face_online_not_supported', detail=_('Online face verification requires Web Terminal'))
            self.face_monitor_token = self.request.query_params.get('face_monitor_token', self.face_monitor_token)
            if not self.face_monitor_token:
                raise JMSException(code='acl_face_online', detail=_('Online face monitoring context is required'))
            from authentication.serializers.face import FaceMonitorContextSerializer
            try:
                self.face_monitor_token = FaceMonitorContextSerializer().fields['face_monitor_token'].run_validation(self.face_monitor_token)
            except ValidationError as error:
                raise ValidationError({'face_monitor_token': error.detail}) from error
        # Preserve the existing request/validation trigger, including while
        # approval or face verification is still pending.
        recipients = {}
        for rule in policy.rules:
            if rule.notice_enabled:
                for recipient in rule.recipients.all():
                    recipients.setdefault(recipient.pk, (recipient, rule))
        os_name = get_request_os(self.request) if self.request else 'windows'
        method = ConnectMethodUtil.get_connect_method(connect_method, protocol=protocol, os=os_name)
        login_from = method['label'] if method else connect_method
        for recipient, rule in recipients.values():
            AssetLoginReminderMsg(recipient, asset, user, account, rule, ip, self.input_username, login_from).publish_async()
        return {
            'requirements': requirements, 'username': username,
            'review_acls': [str(rule.id) for rule in reviews],
            'face_online': policy.enabled('face_online_enabled'),
        }

    def create_face_verify(self, connection_token_id, *, tokens=None):
        if not self.request.user.is_face_code_set:
            raise JMSException(code='no_face_feature', detail=_('No available face feature'))
        with transaction.atomic():
            token = ConnectionToken.objects.select_for_update().get(pk=connection_token_id)
            states = token.acl_context.get('requirements', {})
            if (token.acl_context.get('cancelled') or token.is_expired
                    or token.user_id != self.request.user.id or states.get('face') != 'pending'):
                raise PermissionDenied(_('Face verification is no longer available'))
            if self.request.data.get('retry_face') and any(states.get(key, 'passed') != 'passed' for key in ('reason', 'mfa')):
                raise ValidationError({'step': _('Complete the current connection step first')})
        context_data = {
            "action": "login_asset",
            "connection_token_id": connection_token_id,
        }
        if tokens:
            context_data['connection_token_ids'] = [str(item.pk) for item in tokens]
        face_verify_token = self.create_face_verify_context(
            context_data, user_id=self.request.user.id
        )
        with transaction.atomic(), tmp_to_root_org():
            for item in tokens or [token]:
                item = ConnectionToken.objects.select_for_update().get(pk=item.pk)
                if item.acl_context.get('cancelled'):
                    raise PermissionDenied(_('Connection is no longer available'), code='connection_unavailable')
                item.acl_context['face_token'] = face_verify_token
                item.save(update_fields=['acl_context'])
                if item.pk == token.pk:
                    token = item
        from authentication.services.connection_acl import acl_state
        return {'face_token': face_verify_token, 'acl': acl_state(token)}
