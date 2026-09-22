import hashlib
import json
import shlex
from datetime import timedelta

from django.core import signing
from django.core.cache import cache
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.const import AuditEvent
from accounts.models import (
    CredentialApplicationBinding, CredentialClientInstance,
    CredentialClientStatus, ApplicationCredential, IntegrationApplication,
    ClientAccessConfiguration,
)
from .audit import record
from common.utils import random_string
from common.exceptions import JMSException
from orgs.utils import tmp_to_org


class CredentialClientManager:
    activity_write_interval = timedelta(seconds=60)

    def __init__(self, user, configuration_id=None, instance_id='', audit_context=None):
        self.configuration_id = configuration_id
        self.audit_context = audit_context
        self.application, self.client = self._get_application_and_client(
            user, instance_id
        )
        from accounts.credential_rotation.participants import enroll_client
        enroll_client(self.client)
        if self.audit_context is not None:
            self.audit_context.set_client(self.client)

    def _get_application_and_client(self, user, instance_id):
        if isinstance(user, CredentialClientInstance):
            if not user.is_valid or user.type != CredentialClientInstance.Type.agent:
                raise PermissionDenied(_('The Agent client instance is disabled.'), code=AuditEvent.CLIENT_DISABLED)
            self.configuration = user.configuration
            return user.application, user

        if not self.configuration_id:
            raise ValidationError({'configuration_id': _('This field is required for SDK access.')})
        if not instance_id:
            raise ValidationError({
                'instance_id': _('This field is required for SDK access.')
            })
        self.configuration = ClientAccessConfiguration.objects.filter(
            id=self.configuration_id, application=user,
            type=CredentialClientInstance.Type.sdk, is_active=True,
        ).first()
        if not self.configuration:
            raise PermissionDenied(_('The SDK client access configuration is disabled or invalid.'), code='configuration_disabled')
        client = CredentialClientInstance.objects.get_or_create(
            configuration=self.configuration,
            application=user,
            instance_id=instance_id,
            defaults={'type': CredentialClientInstance.Type.sdk},
        )[0]
        if client.type != CredentialClientInstance.Type.sdk or not client.is_active:
            raise PermissionDenied(_('The SDK client instance is disabled.'), code=AuditEvent.CLIENT_DISABLED)
        return user, client

    def _get_credential(self, key, lock=True):
        base_key, separator, account_id = key.partition(':')
        queryset = ApplicationCredential.objects.all()
        if lock:
            queryset = queryset.select_for_update(of=('self',))
        credential = queryset.select_related(
            'account__asset__platform', 'alternate_account', 'active_account',
        ).filter(key=base_key, is_active=True).first()
        if not credential:
            raise JMSException(_('Credential policy not found.'), code='credential_not_found')

        if not self.configuration.credentials.filter(id=credential.id).exists():
            raise PermissionDenied(_('The client access configuration does not include this credential.'), code='credential_not_selected')
        if not credential.applications.filter(id=self.application.id).exists():
            raise PermissionDenied(_(
                'The credential policy is not bound to this application.'
            ), code='credential_not_bound')
        if credential.mode == ApplicationCredential.Mode.subscription:
            if not separator or not account_id:
                raise JMSException(_('Credential policy not found.'), code='credential_not_found')
            account = self.application.get_accounts().select_related(
                'asset__platform'
            ).filter(id=account_id).first()
            if not account:
                raise PermissionDenied(_(
                    'The application is not authorized for this credential account.'
                ), code='credential_not_authorized')
            return credential, account
        if separator or not credential.authorized_applications().filter(id=self.application.id).exists():
            raise PermissionDenied(_(
                'The application is not authorized for every credential account.'
            ), code='credential_not_authorized')
        return credential, credential.active_account

    def _get_subscription_credential(self, account_id, lock=True):
        queryset = ApplicationCredential.objects.all()
        if lock:
            queryset = queryset.select_for_update(of=('self',))
        credential = queryset.filter(
            id__in=self.configuration.credentials.values('id'),
            applications=self.application,
            mode=ApplicationCredential.Mode.subscription,
            is_active=True,
        ).order_by('key').first()
        if not credential:
            raise PermissionDenied(
                _('The client access configuration does not include an active credential update subscription.'),
                code='credential_not_selected',
            )
        account = self.application.get_accounts().select_related(
            'asset__platform'
        ).filter(id=account_id).first()
        if not account:
            raise PermissionDenied(_(
                'The application is not authorized for this credential account.'
            ), code='credential_not_authorized')
        return credential, account

    def fetch(self, key, remote_addr, account_id=None):
        if account_id:
            credential, account = self._get_subscription_credential(account_id)
            key = credential.account_key(account.id)
        else:
            credential, account = self._get_credential(key)
        revision = (
            account.version if credential.mode == ApplicationCredential.Mode.subscription
            else credential.current_revision
        )
        now = timezone.now()
        binding = CredentialApplicationBinding.objects.get(
            credential=credential, application=self.application
        )
        state = CredentialClientStatus.objects.get_or_create(
            binding=binding, client=self.client
        )[0]
        revision_changed = state.date_fetched is None or state.fetched_revision != revision
        values = {'fetched_revision': revision}
        if credential.status != ApplicationCredential.Status.idle:
            values.update(is_rotation_participant=True, required_revision=credential.revision)
        self._save_status(state, now, values, fetched=True)
        if credential.status != ApplicationCredential.Status.idle:
            from accounts.credential_rotation.participants import ensure_participant
            ensure_participant(credential, state)
        asset = account.asset
        if revision_changed:
            record(
                AuditEvent.CREDENTIAL_FETCHED, credential=credential, client=self.client,
                applications=[self.application], account=account,
                credential_key=key, revision=revision, remote_addr=remote_addr,
            )
        if self.audit_context is not None:
            self.audit_context.set_fetch_result(revision, revision_changed)
        return {
            'key': key,
            'revision': revision,
            'asset': {
                'id': str(asset.id),
                'name': asset.name,
                'address': asset.address,
                'platform': {
                    'id': str(asset.platform_id),
                    'name': asset.platform.name,
                    'category': asset.platform.category,
                    'type': asset.platform.type,
                },
            },
            'account': {
                'id': str(account.id),
                'name': account.name,
                'username': account.username,
                'secret_type': account.secret_type,
                'secret': account.secret,
            },
        }

    def confirm(self, key, revision, account_id):
        credential, account = self._get_credential(key)
        if credential.mode == ApplicationCredential.Mode.subscription:
            raise ValidationError(_('Credential update subscriptions do not require confirmation.'))
        state = CredentialClientStatus.objects.select_related(
            'binding__credential'
        ).filter(
            binding__application=self.application,
            binding__credential__key=key,
            client=self.client,
        ).first()
        if not state:
            raise ValidationError(_('Fetch the credential before confirming it.'))
        if revision != credential.current_revision or account_id != account.id:
            raise ValidationError(_('The credential revision is no longer current.'))
        if revision > state.fetched_revision:
            raise ValidationError(_('Fetch the credential before confirming it.'))

        now = timezone.now()
        self._confirm_status(state, credential, now)
        return {'key': credential.key, 'revision': credential.current_revision}

    def _confirm_status(self, state, credential, now):
        values = {
            'applied_revision': credential.current_revision,
            'applied_account_id': credential.active_account_id,
        }
        if any(getattr(state, field) != value for field, value in values.items()):
            record(AuditEvent.CREDENTIAL_CONFIRMED, credential=credential, client=self.client)
            values['date_applied'] = now
        self._save_status(state, now, values)

    def _save_status(self, state, now, values, fetched=False):
        changed = {field: value for field, value in values.items() if getattr(state, field) != value}
        timestamps = ['date_fetched'] if fetched else []
        for field in timestamps:
            previous = getattr(state, field)
            if changed or previous is None or now - previous >= self.activity_write_interval:
                values[field] = now
        changed.update({field: values[field] for field in timestamps if field in values})
        if not changed:
            return
        for field, value in changed.items():
            setattr(state, field, value)
        state.save(update_fields=[*changed, 'date_updated'])

    @staticmethod
    def credential_keys(configuration):
        keys = []
        accounts = None
        credentials = configuration.credentials.filter(is_active=True).order_by('key')
        for credential in credentials:
            if credential.mode == ApplicationCredential.Mode.subscription:
                if accounts is None:
                    accounts = configuration.application.get_accounts().order_by('id')
                for account in accounts:
                    keys.append(credential.account_key(account.id))
            elif credential.authorized_applications().filter(
                id=configuration.application_id
            ).exists():
                keys.append(credential.key)
        return keys

    @staticmethod
    def confirmation_keys(configuration):
        return list(configuration.credentials.filter(
            is_active=True,
            mode=ApplicationCredential.Mode.alternating_rotation,
            applications=configuration.application,
        ).order_by('key').values_list('key', flat=True))

    @classmethod
    def agent_configuration(cls, configuration):
        root = configuration.install_path.rstrip('/')
        return {
            'delivery_mode': configuration.delivery_mode,
            'credential_keys': cls.credential_keys(configuration),
            'confirmation_keys': cls.confirmation_keys(configuration),
            'delivery_root': f'{root}/credentials/{configuration.id}',
            'socket_path': f'/run/jumpserver-pam/{configuration.id}/agent.sock',
            'app_user': configuration.app_user,
            'systemd_unit': configuration.systemd_unit,
            'systemd_action': configuration.systemd_action,
        }

    @classmethod
    def agent_configuration_digest(cls, configuration):
        payload = cls.agent_configuration(configuration)
        encoded = json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()
        return hashlib.sha256(encoded).hexdigest()

    def update_client_metadata(self, client_version='', protocol_version=1, config_schema_version=None):
        values = {
            'client_version': client_version,
            'protocol_version': protocol_version,
            'config_schema_version': config_schema_version,
        }
        changed = {
            key: value for key, value in values.items()
            if value is not None and getattr(self.client, key) != value
        }
        if not changed:
            return
        CredentialClientInstance.objects.filter(id=self.client.id).update(**changed)
        for key, value in changed.items():
            setattr(self.client, key, value)

    def sync_agent(
        self, config_digest='', credentials=None, delivered_credentials=None,
        sync_status='', sync_error='',
    ):
        if self.client.type != CredentialClientInstance.Type.agent:
            raise PermissionDenied(_('Agent synchronization requires an Agent client.'))
        now = timezone.now()
        self._record_delivered(delivered_credentials or [], now)
        desired = self.agent_configuration(self.configuration)
        desired_digest = self.agent_configuration_digest(self.configuration)
        known = {item['key']: item['revision'] for item in credentials or []}
        metadata = []
        for key in desired['credential_keys']:
            credential, account = self._get_credential(key, lock=False)
            revision = (
                account.version if credential.mode == ApplicationCredential.Mode.subscription
                else credential.current_revision
            )
            metadata.append({
                'key': key,
                'revision': revision,
                'available': True,
                'changed': known.get(key) != revision,
            })
        values = {
            'config_digest': config_digest,
            'sync_status': sync_status,
            'sync_error': sync_error[:128],
            'date_last_synced': now,
        }
        CredentialClientInstance.objects.filter(id=self.client.id).update(**values)
        for key, value in values.items():
            setattr(self.client, key, value)
        response = {
            'config_digest': desired_digest,
            'credentials': metadata,
            'removed_keys': sorted(set(known) - set(desired['credential_keys'])),
            'date_last_synced': now,
        }
        if config_digest != desired_digest:
            response['configuration'] = desired
        return response

    def _record_delivered(self, credentials, now):
        revisions = {item['key']: item['revision'] for item in credentials}
        if not revisions:
            return
        states = CredentialClientStatus.objects.select_related(
            'binding__credential'
        ).filter(
            binding__application=self.application,
            binding__credential__key__in=revisions,
            client=self.client,
        )
        for state in states:
            revision = revisions[state.binding.credential.key]
            if (
                revision == state.binding.credential.current_revision
                and revision == state.fetched_revision
                and revision != state.delivered_revision
            ):
                self._save_status(state, now, {
                    'delivered_revision': revision, 'date_delivered': now,
                })

    @staticmethod
    def register_agent(
        token, instance_id, name='', client_version='',
        protocol_version=1, config_schema_version=1,
    ):
        try:
            payload = signing.loads(
                token, salt='credential-agent-register', max_age=600
            )
        except signing.BadSignature as exc:
            raise ValidationError({
                'token': _('Invalid or expired registration token.')
            }) from exc

        used_key = f"credential-agent-register-used:{payload['nonce']}"
        with tmp_to_org(payload['org_id']):
            application = IntegrationApplication.objects.filter(
                id=payload['application_id'], is_active=True,
            ).first()
            configuration = ClientAccessConfiguration.objects.select_for_update().filter(
                id=payload.get('configuration_id'), application=application,
                type=CredentialClientInstance.Type.agent, is_active=True,
            ).first()
            if not application or not configuration:
                raise ValidationError({
                    'token': _('Client access configuration not found.')
                })
            if CredentialClientInstance.objects.filter(
                configuration=configuration, instance_id=instance_id,
            ).exists():
                raise JMSException(code='client_instance_exists', detail=_(
                    'This client instance already exists. Reuse its local configuration. '
                    'If that configuration was lost, review and remove the unused instance '
                    'or choose a different instance ID; registration will not replace its identity.'
                ))
            if not cache.add(used_key, True, timeout=600):
                raise JMSException(code='registration_token_used', detail=_(
                    'Registration token has already been used. Check whether the instance '
                    'was created before generating a new token.'
                ))

            secret = random_string(48)
            client = CredentialClientInstance.objects.create(
                configuration=configuration,
                instance_id=instance_id,
                application=application,
                type=CredentialClientInstance.Type.agent,
                secret=secret,
                client_version=client_version,
                protocol_version=protocol_version,
                config_schema_version=config_schema_version,
                is_active=True,
                comment=name,
            )
            desired = CredentialClientManager.agent_configuration(configuration)
            desired_digest = CredentialClientManager.agent_configuration_digest(configuration)
        return {
            'agent_id': str(client.id),
            'agent_secret': secret,
            'application_id': str(application.id),
            'configuration_id': str(configuration.id),
            'credential_keys': desired['credential_keys'],
            'configuration': desired,
            'config_digest': desired_digest,
            'org_id': application.org_id,
            'protocol_version': 1,
            'config_schema_version': 1,
        }


class ClientAccessConfigurationManager:
    def __init__(self, configuration):
        self.configuration = configuration

    def materials(self, endpoint):
        configuration = self.configuration
        if not configuration.is_active or not configuration.application.is_active:
            raise ValidationError(_('The client access configuration is disabled.'))
        if configuration.type == CredentialClientInstance.Type.sdk:
            modes = set(configuration.credentials.values_list('mode', flat=True))
            if len(modes) != 1:
                raise ValidationError({
                    'credentials': _('SDK access configurations cannot mix credential policy modes.')
                })
            mode = modes.pop()
            keys = CredentialClientManager.confirmation_keys(configuration)
            app_secret = IntegrationApplication.objects.values_list(
                'secret', flat=True,
            ).get(id=configuration.application_id)
            if mode == ApplicationCredential.Mode.subscription:
                code = render_to_string(
                    'accounts/credential_client/sdk_subscription_example.py.tpl'
                )
                keys = None
            else:
                code = render_to_string(
                    'accounts/credential_client/sdk_rotation_example.py.tpl'
                )
            config = render_to_string('accounts/credential_client/sdk_config.py.tpl', {
                'endpoint': repr(endpoint),
                'app_id': repr(str(configuration.application_id)),
                'app_secret': repr(app_secret),
                'org_id': repr(str(configuration.org_id)),
                'configuration_id': repr(str(configuration.id)),
                'include_keys': keys is not None,
                'credential_keys': repr(keys) if keys is not None else None,
                'confirmation_keys': repr(keys) if keys is not None else None,
            })
            return {
                'type': 'sdk', 'config': config, 'code': code, 'filename': 'jms_pam_config.py',
                'install_command': 'python3 -m pip install --upgrade jms-pam',
            }
        token = signing.dumps({
            'application_id': str(configuration.application_id),
            'configuration_id': str(configuration.id),
            'org_id': str(configuration.org_id),
            'nonce': random_string(24),
        }, salt='credential-agent-register')
        path = configuration.install_path.rstrip('/')
        command = (
            f'sudo python3 -m venv {shlex.quote(path + "/venv")} && '
            f'sudo {shlex.quote(path + "/venv/bin/pip")} install --upgrade jms-pam && '
            f'sudo {shlex.quote(path + "/venv/bin/jms-pam-agent")} install --endpoint {shlex.quote(endpoint)} '
            f'--token {shlex.quote(token)} --instance-id "$(hostname)" '
            f'--configuration-id {shlex.quote(str(configuration.id))} '
            f'--app-user {shlex.quote(configuration.app_user)} '
            f'--install-path {shlex.quote(path)}'
        )
        return {
            'type': 'agent', 'expires_in': 600, 'install_command': command,
        }
