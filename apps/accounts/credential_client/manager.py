import json
import shlex

from django.core import signing
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.models import (
    CredentialApplicationBinding, CredentialClientInstance,
    CredentialClientStatus, ApplicationCredential, IntegrationApplication,
    ClientAccessConfiguration,
)
from audits.models import IntegrationApplicationLog
from common.utils import random_string
from orgs.utils import tmp_to_org


class CredentialClientManager:
    def __init__(self, user, configuration_id=None, instance_id=''):
        self.configuration_id = configuration_id
        self.application, self.client = self._get_application_and_client(
            user, instance_id
        )

    def _get_application_and_client(self, user, instance_id):
        if isinstance(user, CredentialClientInstance):
            if not user.is_valid or user.type != CredentialClientInstance.Type.agent:
                raise PermissionDenied(_('The Agent client instance is disabled.'))
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
            raise PermissionDenied(_('The SDK client access configuration is disabled or invalid.'))
        client = CredentialClientInstance.objects.get_or_create(
            configuration=self.configuration,
            application=user,
            instance_id=instance_id,
            defaults={'type': CredentialClientInstance.Type.sdk},
        )[0]
        if client.type != CredentialClientInstance.Type.sdk or not client.is_active:
            raise PermissionDenied(_('The SDK client instance is disabled.'))
        return user, client

    def _get_credential(self, key):
        credential = ApplicationCredential.objects.select_for_update(of=('self',)).select_related(
            'primary_account__asset__platform', 'backup_account',
            'published_account',
        ).filter(key=key, is_active=True).first()
        if not credential:
            raise ValidationError({'key': _('Application credential not found.')})

        if not self.configuration.credentials.filter(id=credential.id).exists():
            raise PermissionDenied(_('The client access configuration does not include this credential.'))
        account_ids = {credential.primary_account_id}
        if credential.backup_account_id:
            account_ids.add(credential.backup_account_id)
        allowed = set(
            self.application.get_accounts().filter(
                id__in=account_ids
            ).values_list('id', flat=True)
        )
        if allowed != account_ids:
            raise PermissionDenied(_(
                'The application is not authorized for every credential account.'
            ))
        return credential

    def fetch(self, key, remote_addr):
        credential = self._get_credential(key)
        if (
            credential.rotation_mode == ApplicationCredential.RotationMode.single
            and credential.status == ApplicationCredential.Status.changing_secret
        ):
            raise ValidationError(_('The account secret is changing. Retry after the new revision is published.'))
        now = timezone.now()
        binding = CredentialApplicationBinding.objects.get_or_create(
            credential=credential, application=self.application
        )[0]
        state = CredentialClientStatus.objects.get_or_create(
            binding=binding, client=self.client
        )[0]
        state.fetched_revision = credential.current_revision
        if credential.status != ApplicationCredential.Status.idle:
            state.is_rotation_participant = True
            state.required_revision = credential.revision
        state.date_fetched = now
        state.date_last_seen = now
        state.save(update_fields=[
            'fetched_revision', 'date_fetched', 'date_last_seen', 'date_updated',
            'is_rotation_participant', 'required_revision',
        ])
        self._touch(now)

        account = credential.published_account
        asset = account.asset
        IntegrationApplicationLog.objects.create(
            remote_addr=remote_addr,
            service=self.application.name,
            service_id=self.application.id,
            account=f'{account.name}({account.username})',
            asset=f'{asset.name}({asset.address})',
        )
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
        states_by_key = {
            state.binding.credential.key: state for state in states
        }
        updated = []
        for item in sorted(credentials, key=lambda item: item['key']):
            credential = self._get_credential(item['key'])
            state = states_by_key.get(item['key'])
            if not state:
                continue
            if (
                item['account_id'] != credential.published_account_id
                or item['revision'] != credential.current_revision
                or item['revision'] > state.fetched_revision
            ):
                state.date_last_seen = now
                state.save(update_fields=['date_last_seen'])
                continue
            state.applied_revision = item['revision']
            state.applied_account_id = item['account_id']
            state.date_last_seen = now
            state.date_applied = now
            state.save(update_fields=[
                'applied_revision', 'applied_account', 'date_applied',
                'date_last_seen', 'date_updated',
            ])
            updated.append(credential.key)
        self._touch(now)
        return {'updated': updated, 'date_last_seen': now}

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
        state.applied_revision = credential.current_revision
        state.applied_account = credential.published_account
        state.date_applied = now
        state.date_last_seen = now
        state.save(update_fields=[
            'applied_revision', 'applied_account', 'date_applied',
            'date_last_seen', 'date_updated',
        ])
        self._touch(now)
        return {'key': credential.key, 'revision': credential.current_revision}

    def _touch(self, now):
        CredentialClientInstance.objects.filter(id=self.client.id).update(
            date_last_seen=now
        )

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
            configuration = ClientAccessConfiguration.objects.filter(
                id=payload.get('configuration_id'), application=application,
                type=CredentialClientInstance.Type.agent, is_active=True,
            ).first()
            if not application or not configuration:
                raise ValidationError({
                    'token': _('Client access configuration not found.')
                })
            if not cache.add(used_key, True, timeout=600):
                raise ValidationError({
                    'token': _('Registration token has already been used.')
                })

            secret = random_string(48)
            if CredentialClientInstance.objects.filter(
                configuration=configuration, instance_id=instance_id, is_active=False,
            ).exists():
                raise PermissionDenied(_('Enable the disabled client instance before registering it again.'))
            client = CredentialClientInstance.objects.update_or_create(
                configuration=configuration,
                instance_id=instance_id,
                defaults={
                    'application': application,
                    'type': CredentialClientInstance.Type.agent,
                    'secret': secret,
                    'is_active': True,
                    'comment': name,
                },
            )[0]
        return {
            'agent_id': str(client.id),
            'agent_secret': secret,
            'application_id': str(application.id),
            'configuration_id': str(configuration.id),
            'credential_keys': list(configuration.credentials.values_list('key', flat=True)),
            'org_id': application.org_id,
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
        }
        if configuration.type == CredentialClientInstance.Type.sdk:
            config['app_secret'] = configuration.application.secret
            code = (
                'from jms_pam import JumpServerPAMClient\n\n'
                "with JumpServerPAMClient.from_config('jms-pam.json') as client:\n"
                f'    for key in {json.dumps(keys)}:\n'
                '        credential = client.get_credential(key)\n'
                '        # Connect/reload your application using credential.username and credential.secret.\n'
                '        # Confirm ONLY after the application is using this version:\n'
                '        # client.confirm_applied(credential)\n'
            )
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
