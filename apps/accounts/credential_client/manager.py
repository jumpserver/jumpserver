import hashlib
import json
from datetime import timedelta
from uuid import UUID

from accounts.const import AuditEvent
from accounts.models import (
    ApplicationCredential,
    CredentialApplicationBinding,
    CredentialClientInstance,
    CredentialClientStatus,
)
from common.exceptions import JMSException
from django.db.models import Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied, ValidationError

from .audit import record


def scope_uses_credential(scope, credential):
    if scope is None:
        return True
    if credential.key in scope['keys']:
        return True
    return bool(set(scope['account_ids']) & {
        str(credential.account_id), str(credential.alternate_account_id),
    })


def client_uses_credential(client, credential):
    if client.type == CredentialClientInstance.Type.agent and not client.date_last_synced:
        return False
    scope = client.delivery_scope if client.type == CredentialClientInstance.Type.agent else None
    return scope_uses_credential(scope, credential)


class CredentialClientManager:
    activity_write_interval = timedelta(seconds=60)

    def __init__(self, user, instance_id='', audit_context=None,
                 client_type='sdk'):
        self.client_type = client_type
        self.audit_context = audit_context
        self.application, self.client = self._get_application_and_client(
            user, instance_id
        )
        from accounts.credential_rotation.participants import enroll_client
        if self.client.type != CredentialClientInstance.Type.agent:
            enroll_client(self.client)
        if self.audit_context is not None:
            self.audit_context.set_client(self.client)

    def _get_application_and_client(self, user, instance_id):
        if isinstance(user, CredentialClientInstance):
            if not user.is_valid or user.type != CredentialClientInstance.Type.agent:
                raise PermissionDenied(_('The Agent client instance is disabled.'), code=AuditEvent.CLIENT_DISABLED)
            return user.application, user

        if not instance_id:
            raise ValidationError({
                'instance_id': _('This field is required for client access.')
            })
        if not user.is_active:
            raise PermissionDenied(_('The application is disabled.'), code=AuditEvent.CLIENT_DISABLED)
        client = CredentialClientInstance.objects.get_or_create(
            application=user, type=self.client_type, instance_id=instance_id,
        )[0]
        if client.type != self.client_type or not client.is_active:
            raise PermissionDenied(_('The client instance is disabled.'), code=AuditEvent.CLIENT_DISABLED)
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

        if not credential.applications.filter(id=self.application.id).exists():
            raise PermissionDenied(_(
                'The credential policy is not bound to this application.'
            ), code='credential_not_bound')
        if credential.mode == ApplicationCredential.Mode.subscription:
            # Accept pre-account-key selectors during client upgrades. New push
            # scopes and events use account:<uuid> and never emit this alias.
            if not separator or not account_id:
                raise JMSException(_('Credential policy not found.'), code='credential_not_found')
            if not credential.subscription_all_authorized and not credential.subscription_accounts.filter(
                id=account_id
            ).exists():
                raise PermissionDenied(_(
                    'This account is not selected by the credential change subscription.'
                ), code='credential_not_selected')
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

    def _subscription_credentials(self, account_id, lock=True):
        """Find the push subscriptions covering one application-authorized account."""
        account = self.application.get_accounts().select_related(
            'asset__platform'
        ).filter(id=account_id).first()
        if not account:
            raise PermissionDenied(_(
                'The application is not authorized for this credential account.'
            ), code='credential_not_authorized')
        credentials = ApplicationCredential.objects.filter(
            applications=self.application,
            mode=ApplicationCredential.Mode.subscription,
            is_active=True,
        ).filter(
            Q(subscription_all_authorized=True) | Q(subscription_accounts=account)
        ).distinct().order_by('key')
        if lock:
            credentials = ApplicationCredential.objects.filter(
                id__in=credentials.values('id')
            ).select_for_update(of=('self',)).order_by('key')
        credentials = list(credentials)
        if not credentials:
            raise PermissionDenied(_(
                'The application does not include an active credential change subscription.'
            ), code='credential_not_selected')
        return credentials, account

    def fetch_account(self, account_id, remote_addr):
        """Pull access is granted by the application, independently of push policies."""
        account = self.application.get_accounts().select_related(
            'asset__platform'
        ).filter(id=account_id).first()
        if not account:
            raise PermissionDenied(_(
                'The application is not authorized for this credential account.'
            ), code='credential_not_authorized')
        revision = account.version
        key = f'account:{account.id}'
        payload = self._account_payload(key, revision, account)
        from accounts.credential_rotation.preparation import record_secret_access
        record_secret_access(account, self.application)
        record(
            AuditEvent.CREDENTIAL_FETCHED, client=self.client, account=account,
            credential_key=key, revision=revision, remote_addr=remote_addr,
        )
        if self.audit_context is not None:
            self.audit_context.set_fetch_result(revision, True)
        return payload

    def fetch(self, key, remote_addr, account_id=None):
        self.application.assert_account_limit()
        if account_id:
            return self.fetch_account(account_id, remote_addr)
        if key.startswith('account:'):
            try:
                push_account_id = UUID(key.removeprefix('account:'))
            except ValueError:
                raise JMSException(_('Credential account not found.'), code='credential_not_found')
            if key != ApplicationCredential.account_key(push_account_id):
                raise JMSException(_('Credential account not found.'), code='credential_not_found')
            credentials, account = self._subscription_credentials(push_account_id)
            revision = account.version
            payload = self._account_payload(key, revision, account)
            from accounts.credential_rotation.preparation import record_secret_access
            record_secret_access(account, self.application)
            now = timezone.now()
            any_revision_changed = False
            for credential in credentials:
                binding = CredentialApplicationBinding.objects.get(
                    credential=credential, application=self.application,
                )
                state = CredentialClientStatus.objects.get_or_create(
                    binding=binding, client=self.client,
                )[0]
                revision_changed = state.date_fetched is None or state.fetched_revision != revision
                any_revision_changed |= revision_changed
                self._save_status(state, now, {'fetched_revision': revision}, fetched=True)
                if revision_changed:
                    record(
                        AuditEvent.CREDENTIAL_FETCHED, credential=credential,
                        client=self.client, applications=[self.application], account=account,
                        credential_key=key, revision=revision, remote_addr=remote_addr,
                    )
            if self.audit_context is not None:
                self.audit_context.set_fetch_result(revision, any_revision_changed)
            return payload
        credential, account = self._get_credential(key)
        revision = (
            account.version if credential.mode == ApplicationCredential.Mode.subscription
            else credential.current_revision
        )
        payload = self._account_payload(key, revision, account)
        if credential.account_switch:
            payload['account_switch'] = credential.account_switch
        from accounts.credential_rotation.preparation import record_secret_access
        record_secret_access(account, self.application)
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
        if revision_changed:
            record(
                AuditEvent.CREDENTIAL_FETCHED, credential=credential, client=self.client,
                applications=[self.application], account=account,
                credential_key=key, revision=revision, remote_addr=remote_addr,
            )
        if self.audit_context is not None:
            self.audit_context.set_fetch_result(revision, revision_changed)
        return payload

    @staticmethod
    def _account_payload(key, revision, account):
        return {
            'key': key,
            'revision': revision,
            'asset': {
                'id': str(account.asset.id),
                'name': account.asset.name,
                'address': account.asset.address,
                'platform': {
                    'id': str(account.asset.platform_id),
                    'name': account.asset.platform.name,
                    'category': account.asset.platform.category,
                    'type': account.asset.platform.type,
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

    def authorized_accounts(self, limit=200, offset=0, search=''):
        """List the current scope without reading secrets or recording a fetch."""
        self.application.assert_account_limit()
        queryset = self.application.get_accounts().select_related('asset__platform')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(username__icontains=search) |
                Q(asset__name__icontains=search) | Q(asset__address__icontains=search)
            )
        count = queryset.count()
        ordered = queryset.order_by('id')
        page = list(ordered[offset:offset + limit])
        page_by_id = {account.id: account for account in page}
        accounts = {}
        for account in page:
            account_id = str(account.id)
            asset = account.asset
            accounts[account.id] = {
                'id': account_id, 'name': account.name,
                'username': account.username, 'secret_type': account.secret_type,
                'asset': {
                    'id': str(asset.id), 'name': asset.name, 'address': asset.address,
                    'platform': {
                        'id': str(asset.platform_id), 'name': asset.platform.name,
                        'category': asset.platform.category, 'type': asset.platform.type,
                    },
                },
                'credentials': [],
            }
        subscribed = set()
        for credential in ApplicationCredential.objects.filter(
            is_active=True, applications=self.application,
        ).distinct().order_by('key'):
            if credential.mode == ApplicationCredential.Mode.subscription:
                selected = set(accounts) if credential.subscription_all_authorized else set(
                    credential.subscription_accounts.filter(id__in=accounts).values_list('id', flat=True)
                )
                for account_id in selected:
                    subscribed.add(account_id)
            elif credential.authorized_applications().filter(id=self.application.id).exists():
                account = accounts.get(credential.active_account_id)
                if account:
                    account['credentials'].append({
                        'key': credential.key, 'mode': credential.mode,
                        'revision': credential.current_revision,
                        'account_switch': credential.account_switch,
                    })
        for account_id in subscribed:
            accounts[account_id]['credentials'].append({
                'key': ApplicationCredential.account_key(account_id),
                'mode': ApplicationCredential.Mode.subscription,
                'revision': page_by_id[account_id].version,
            })
        return {'count': count, 'accounts': list(accounts.values())}

    def confirm(self, key, revision, account_id):
        credential, account = self._get_credential(key)
        if credential.mode == ApplicationCredential.Mode.subscription:
            raise ValidationError(_('Credential change subscriptions do not require confirmation.'))
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

        from accounts.credential_rotation.preparation import refresh
        refresh(credential)

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
    def credential_keys(application, delivery_scope=None):
        application.assert_account_limit()
        keys = set()
        accounts = None
        selected_keys = set(delivery_scope['keys']) if delivery_scope is not None else None
        selected_accounts = set(delivery_scope['account_ids']) if delivery_scope is not None else None
        credentials = ApplicationCredential.objects.filter(
            applications=application, is_active=True,
        ).order_by('key')
        for credential in credentials:
            if credential.mode == ApplicationCredential.Mode.subscription:
                if accounts is None:
                    accounts = application.get_accounts().order_by('id')
                selected = accounts if credential.subscription_all_authorized else accounts.filter(
                    id__in=credential.subscription_accounts.values('id')
                )
                for account in selected:
                    key = credential.account_key(account.id)
                    if selected_keys is None or key in selected_keys or str(account.id) in selected_accounts:
                        keys.add(key)
            elif credential.authorized_applications().filter(
                id=application.id
            ).exists():
                if selected_keys is None or credential.key in selected_keys or bool(
                    selected_accounts & {str(credential.account_id), str(credential.alternate_account_id)}
                ):
                    keys.add(credential.key)
        return sorted(keys)

    @staticmethod
    def confirmation_keys(application):
        return list(ApplicationCredential.objects.filter(
            is_active=True,
            mode=ApplicationCredential.Mode.alternating_rotation,
            applications=application,
        ).order_by('key').values_list('key', flat=True))

    @classmethod
    def agent_configuration(cls, application, delivery_scope=None):
        keys = cls.credential_keys(application, delivery_scope)
        return {
            'credential_keys': keys,
            'confirmation_keys': [key for key in cls.confirmation_keys(application) if key in keys],
        }

    @classmethod
    def agent_configuration_digest(cls, application, delivery_scope=None):
        payload = cls.agent_configuration(application, delivery_scope)
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
        sync_status='', sync_error='', restart_supported=False, delivery_scope=None,
    ):
        if self.client.type != CredentialClientInstance.Type.agent:
            raise PermissionDenied(_('Agent synchronization requires an Agent client.'))
        # A participant cannot evade an in-progress rotation by narrowing its
        # local selectors. It must finish or the operator must cancel the cycle.
        active = CredentialClientStatus.objects.filter(
            client=self.client, is_rotation_participant=True,
        ).exclude(binding__credential__status=ApplicationCredential.Status.idle).select_related('binding__credential')
        if any(not scope_uses_credential(delivery_scope, state.binding.credential) for state in active):
            raise ValidationError(_('Finish or cancel the current rotation before removing an Agent account rule.'))
        now = timezone.now()
        self._record_delivered(delivered_credentials or [], now)
        desired = self.agent_configuration(self.application, delivery_scope)
        desired_digest = self.agent_configuration_digest(self.application, delivery_scope)
        known = {item['key']: item['revision'] for item in credentials or []}
        metadata = []
        for key in desired['credential_keys']:
            if key.startswith('account:'):
                _, account = self._subscription_credentials(UUID(key.removeprefix('account:')), lock=False)
                revision = account.version
            else:
                credential, _ = self._get_credential(key, lock=False)
                revision = credential.current_revision
            item = {
                'key': key,
                'revision': revision,
                'available': True,
                'changed': known.get(key) != revision,
            }
            if not key.startswith('account:') and credential.account_switch:
                item['account_switch'] = credential.account_switch
            metadata.append(item)
        values = {
            'delivery_scope': delivery_scope,
            'config_digest': config_digest,
            'sync_status': sync_status,
            'sync_error': sync_error[:128],
            'restart_supported': restart_supported,
            'date_last_synced': now,
        }
        CredentialClientInstance.objects.filter(id=self.client.id).update(**values)
        for key, value in values.items():
            setattr(self.client, key, value)
        from accounts.credential_rotation.participants import enroll_client
        enroll_client(self.client)
        response = {
            'config_digest': desired_digest,
            'scope': desired,
            'credentials': metadata,
            'removed_keys': sorted(set(known) - set(desired['credential_keys'])),
            'date_last_synced': now,
        }
        return response

    def _record_delivered(self, credentials, now):
        revisions = {item['key']: item['revision'] for item in credentials}
        if not revisions:
            return
        subscription_revisions = {}
        for key, revision in revisions.items():
            if key.startswith('account:'):
                try:
                    account_id = UUID(key.removeprefix('account:'))
                except ValueError:
                    continue
                if key == ApplicationCredential.account_key(account_id):
                    subscription_revisions[account_id] = revision
        for account_id, revision in subscription_revisions.items():
            try:
                policies, account = self._subscription_credentials(account_id, lock=False)
            except PermissionDenied:
                continue
            if account.version != revision:
                continue
            states = CredentialClientStatus.objects.filter(
                binding__application=self.application,
                binding__credential__in=policies,
                client=self.client,
            )
            for state in states:
                if revision == state.fetched_revision and revision != state.delivered_revision:
                    self._save_status(state, now, {
                        'delivered_revision': revision, 'date_delivered': now,
                    })
        revisions = {key: revision for key, revision in revisions.items() if not key.startswith('account:')}
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
