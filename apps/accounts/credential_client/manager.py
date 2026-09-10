import json
import shlex
from datetime import timedelta

from django.core import signing
from django.core.cache import cache
from django.db.models import Q
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
        queryset = ApplicationCredential.objects.all()
        if lock:
            queryset = queryset.select_for_update(of=('self',))
        credential = queryset.select_related(
            'primary_account__asset__platform', 'backup_account',
            'published_account',
        ).filter(key=key, is_active=True).first()
        if not credential:
            raise JMSException(_('Application credential not found.'), code='credential_not_found')

        if not self.configuration.credentials.filter(id=credential.id).exists():
            raise PermissionDenied(_('The client access configuration does not include this credential.'), code='credential_not_selected')
        if not credential.authorized_applications().filter(id=self.application.id).exists():
            raise PermissionDenied(_(
                'The application is not authorized for every credential account.'
            ), code='credential_not_authorized')
        return credential

    def fetch(self, key, remote_addr):
        credential = self._get_credential(key)
        if (
            credential.rotation_mode == ApplicationCredential.RotationMode.single
            and credential.status in (
                ApplicationCredential.Status.changing_secret,
                ApplicationCredential.Status.recovery_required,
            )
        ):
            raise JMSException(_('The account secret is changing. Retry after the new revision is published.'), code='credential_changing')
        now = timezone.now()
        binding = CredentialApplicationBinding.objects.get_or_create(
            credential=credential, application=self.application
        )[0]
        state = CredentialClientStatus.objects.get_or_create(
            binding=binding, client=self.client
        )[0]
        revision_changed = state.fetched_revision != credential.current_revision
        values = {'fetched_revision': credential.current_revision}
        if credential.status != ApplicationCredential.Status.idle:
            values.update(is_rotation_participant=True, required_revision=credential.revision)
        self._save_status(state, now, values, fetched=True)
        self._touch(now)

        account = credential.published_account
        asset = account.asset
        if revision_changed:
            record(AuditEvent.CREDENTIAL_FETCHED, credential=credential, client=self.client, remote_addr=remote_addr)
        if self.audit_context is not None:
            self.audit_context.set_fetch_result(credential.current_revision, revision_changed)
        return {
            'key': credential.key,
            'revision': credential.current_revision,
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

    def heartbeat(self, credentials):
        now = timezone.now()
        states = CredentialClientStatus.objects.select_related(
            'binding__credential'
        ).filter(
            binding__application=self.application,
            binding__credential__key__in=[item['key'] for item in credentials],
            client=self.client,
        )
        updated = []
        errors = []
        for item in sorted(credentials, key=lambda item: item['key']):
            try:
                credential = self._get_credential(item['key'])
            except (PermissionDenied, JMSException) as exc:
                code = exc.get_codes()
                if code not in ('credential_not_found', 'credential_not_selected', 'credential_not_authorized'):
                    raise
                errors.append({'key': item['key'], 'code': code, 'detail': str(exc.detail)})
                continue
            # Read after taking the credential lock, so concurrent confirmations
            # cannot turn a repeated version into another state transition.
            state = states.filter(binding__credential=credential).first()
            if not state:
                errors.append({'key': item['key'], 'code': 'credential_not_fetched',
                               'detail': str(_('Fetch the credential before confirming it.'))})
                continue
            if (
                item['account_id'] != credential.published_account_id
                or item['revision'] != credential.current_revision
                or item['revision'] > state.fetched_revision
            ):
                self._save_status(state, now, {})
                errors.append({'key': item['key'], 'code': 'credential_revision_mismatch',
                               'detail': str(_('The credential revision is no longer current.'))})
                continue
            self._confirm_status(state, credential, now)
            updated.append(credential.key)
        self._touch(now)
        return {'updated': updated, 'errors': errors, 'date_last_seen': now}

    def confirm(self, key, revision, account_id):
        credential = self._get_credential(key)
        state = CredentialClientStatus.objects.select_related(
            'binding__credential'
        ).filter(
            binding__application=self.application,
            binding__credential__key=key,
            client=self.client,
        ).first()
        if not state:
            raise ValidationError(_('Fetch the credential before confirming it.'))
        if revision != credential.current_revision or account_id != credential.published_account_id:
            raise ValidationError(_('The credential revision is no longer current.'))
        if revision > state.fetched_revision:
            raise ValidationError(_('Fetch the credential before confirming it.'))

        now = timezone.now()
        self._confirm_status(state, credential, now)
        self._touch(now)
        return {'key': credential.key, 'revision': credential.current_revision}

    def _confirm_status(self, state, credential, now):
        values = {
            'applied_revision': credential.current_revision,
            'applied_account_id': credential.published_account_id,
        }
        if any(getattr(state, field) != value for field, value in values.items()):
            record(AuditEvent.CREDENTIAL_CONFIRMED, credential=credential, client=self.client)
            values['date_applied'] = now
        self._save_status(state, now, values)

    def _save_status(self, state, now, values, fetched=False):
        changed = {field: value for field, value in values.items() if getattr(state, field) != value}
        timestamps = ['date_last_seen', 'date_fetched'] if fetched else ['date_last_seen']
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

    def _touch(self, now):
        cutoff = now - self.activity_write_interval
        if self.client.date_last_seen and self.client.date_last_seen > cutoff:
            return
        changed = CredentialClientInstance.objects.filter(id=self.client.id).filter(
            Q(date_last_seen__isnull=True) | Q(date_last_seen__lte=cutoff)
        ).update(date_last_seen=now)
        if changed:
            self.client.date_last_seen = now

    @staticmethod
    def register_agent(token, instance_id, name=''):
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
                is_active=True,
                comment=name,
            )
        return {
            'agent_id': str(client.id),
            'agent_secret': secret,
            'application_id': str(application.id),
            'configuration_id': str(configuration.id),
            'credential_keys': list(configuration.credentials.values_list('key', flat=True)),
            'org_id': application.org_id,
            'notification_enabled': configuration.notification_enabled,
            'notification_url': configuration.notification_url,
        }


class ClientAccessConfigurationManager:
    def __init__(self, configuration):
        self.configuration = configuration

    def materials(self, endpoint):
        configuration = self.configuration
        if not configuration.is_active or not configuration.application.is_active:
            raise ValidationError(_('The client access configuration is disabled.'))
        keys = list(configuration.credentials.values_list('key', flat=True))
        config = {
            'endpoint': endpoint,
            'app_id': str(configuration.application_id),
            'configuration_id': str(configuration.id),
            'org_id': str(configuration.org_id),
            'credential_keys': keys,
            'notification_enabled': configuration.notification_enabled,
        }
        if configuration.type == CredentialClientInstance.Type.sdk:
            config['app_secret'] = configuration.application.secret
            code = render_to_string('accounts/credential_client/sdk_example.py.tpl', {
                'credential_keys': json.dumps(keys),
                'notification_enabled': configuration.notification_enabled,
            })
            return {
                'type': 'sdk', 'config': config, 'code': code, 'filename': 'jms-pam.json',
                'install_command': (
                    'python3 -m pip install --index-url https://pypi.org/simple '
                    f'{shlex.quote(endpoint + "/api/v1/accounts/python-sdk/")}'
                ),
            }
        token = signing.dumps({
            'application_id': str(configuration.application_id),
            'configuration_id': str(configuration.id),
            'org_id': str(configuration.org_id),
            'nonce': random_string(24),
        }, salt='credential-agent-register')
        path = configuration.install_path.rstrip('/')
        credentials = ' '.join(f'--credential {shlex.quote(key)}' for key in keys)
        command = (
            f'sudo python3 -m venv {shlex.quote(path + "/venv")} && '
            f'sudo {shlex.quote(path + "/venv/bin/pip")} install --index-url https://pypi.org/simple '
            f'{shlex.quote(endpoint + "/api/v1/accounts/python-sdk/")} && '
            f'sudo {shlex.quote(path + "/venv/bin/jms-pam-agent")} install --endpoint {shlex.quote(endpoint)} '
            f'--token {shlex.quote(token)} --instance-id "$(hostname)" {credentials} '
            f'--app-user {shlex.quote(configuration.app_user)}'
        )
        return {
            'type': 'agent', 'expires_in': 600, 'install_command': command,
        }
