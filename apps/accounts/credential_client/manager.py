from django.core import signing
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.models import (
    CredentialApplicationBinding, CredentialClientInstance,
    CredentialClientStatus, CredentialPolicy, IntegrationApplication,
)
from audits.models import IntegrationApplicationLog
from common.utils import random_string
from orgs.utils import tmp_to_org


class CredentialClientManager:
    def __init__(self, user, instance_id=''):
        self.application, self.client = self._get_application_and_client(
            user, instance_id
        )

    @staticmethod
    def _get_application_and_client(user, instance_id):
        if isinstance(user, CredentialClientInstance):
            if user.application.credential_access_mode != IntegrationApplication.AccessMode.agent:
                raise PermissionDenied(_(
                    'The application does not use Agent access mode.'
                ))
            return user.application, user

        if user.credential_access_mode != IntegrationApplication.AccessMode.sdk:
            raise PermissionDenied(_(
                'The application does not use SDK access mode.'
            ))
        if not instance_id:
            raise ValidationError({
                'instance_id': _('This field is required for SDK access.')
            })
        client = CredentialClientInstance.objects.get_or_create(
            application=user,
            instance_id=instance_id,
            defaults={'type': CredentialClientInstance.Type.sdk},
        )[0]
        if client.type != CredentialClientInstance.Type.sdk or not client.is_active:
            raise PermissionDenied(_('The SDK client instance is disabled.'))
        return user, client

    def _get_policy(self, key):
        policy = CredentialPolicy.objects.select_related(
            'primary_account__asset__platform', 'backup_account',
            'published_account',
        ).filter(key=key, is_active=True).first()
        if not policy:
            raise ValidationError({'key': _('Credential policy not found.')})

        account_ids = {policy.primary_account_id, policy.backup_account_id}
        allowed = set(
            self.application.get_accounts().filter(
                id__in=account_ids
            ).values_list('id', flat=True)
        )
        if allowed != account_ids:
            raise PermissionDenied(_(
                'The application is not authorized for both policy accounts.'
            ))
        return policy

    def fetch(self, key, remote_addr):
        policy = self._get_policy(key)
        now = timezone.now()
        binding = CredentialApplicationBinding.objects.get_or_create(
            policy=policy, application=self.application
        )[0]
        state = CredentialClientStatus.objects.get_or_create(
            binding=binding, client=self.client
        )[0]
        state.fetched_revision = policy.revision
        state.date_fetched = now
        state.date_last_seen = now
        state.save(update_fields=[
            'fetched_revision', 'date_fetched', 'date_last_seen', 'date_updated',
        ])
        self._touch(now)

        account = policy.published_account
        asset = account.asset
        IntegrationApplicationLog.objects.create(
            remote_addr=remote_addr,
            service=self.application.name,
            service_id=self.application.id,
            account=f'{account.name}({account.username})',
            asset=f'{asset.name}({asset.address})',
        )
        return {
            'key': policy.key,
            'revision': policy.revision,
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
            'binding__policy'
        ).filter(
            binding__application=self.application,
            binding__policy__key__in=[item['key'] for item in credentials],
            client=self.client,
        )
        states_by_key = {
            state.binding.policy.key: state for state in states
        }
        updated = []
        for item in credentials:
            state = states_by_key.get(item['key'])
            if not state:
                continue
            policy = state.binding.policy
            if item['account_id'] not in (
                policy.primary_account_id, policy.backup_account_id
            ):
                continue
            state.applied_revision = item['revision']
            state.applied_account_id = item['account_id']
            state.date_last_seen = now
            state.date_applied = now
            state.save(update_fields=[
                'applied_revision', 'applied_account', 'date_applied',
                'date_last_seen', 'date_updated',
            ])
            updated.append(policy.key)
        self._touch(now)
        return {'updated': updated, 'date_last_seen': now}

    def confirm(self, key, revision, account_id):
        state = CredentialClientStatus.objects.select_related(
            'binding__policy'
        ).filter(
            binding__application=self.application,
            binding__policy__key=key,
            client=self.client,
        ).first()
        if not state:
            raise ValidationError(_('Fetch the credential before confirming it.'))
        policy = state.binding.policy
        if revision != policy.revision or account_id != policy.published_account_id:
            raise ValidationError(_('The credential revision is no longer current.'))

        now = timezone.now()
        state.applied_revision = policy.revision
        state.applied_account = policy.published_account
        state.date_applied = now
        state.date_last_seen = now
        state.save(update_fields=[
            'applied_revision', 'applied_account', 'date_applied',
            'date_last_seen', 'date_updated',
        ])
        self._touch(now)
        return {'key': policy.key, 'revision': policy.revision}

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
                credential_access_mode=IntegrationApplication.AccessMode.agent,
            ).first()
            if not application:
                raise ValidationError({
                    'token': _('Integration application not found.')
                })
            if not cache.add(used_key, True, timeout=600):
                raise ValidationError({
                    'token': _('Registration token has already been used.')
                })

            secret = random_string(48)
            client = CredentialClientInstance.objects.update_or_create(
                application=application,
                instance_id=instance_id,
                defaults={
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
            'org_id': application.org_id,
        }
