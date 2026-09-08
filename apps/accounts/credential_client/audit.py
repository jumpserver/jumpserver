"""Application audit snapshots and credential-fetch state transitions."""
import json
from dataclasses import dataclass
from hashlib import sha256

from django.core.cache import cache
from django.db import transaction
from redis.exceptions import RedisError

from accounts.const import AuditSource
from accounts.models import ApplicationAudit, CredentialClientInstance, IntegrationApplication
from common.utils import get_logger, get_request_ip
from jumpserver.utils import get_current_request
from orgs.utils import tmp_to_org

logger = get_logger(__name__)


def record(event, *, application=None, credential=None, client=None, configuration=None, **values):
    if client:
        application, configuration = client.application, client.configuration
        values.update(instance_id=client.instance_id)
    obj = application or credential or configuration
    if obj is None:
        raise ValueError('Audit requires a trusted organization context')
    if configuration:
        application = configuration.application
        values.update(configuration=configuration.name, configuration_id=configuration.id)
    if application:
        values.update(service=application.name, service_id=application.id)
    if credential:
        rotation = credential.rotation_records.order_by('-date_created').first()
        values.update(
            credential=credential.name, credential_id=credential.id,
            credential_key=credential.key, revision=credential.current_revision,
            rotation_id=rotation.id if rotation else None,
        )
    request = get_current_request()
    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False) and not isinstance(user, (IntegrationApplication, CredentialClientInstance)):
        source = AuditSource.ADMINISTRATOR
    elif client:
        source = AuditSource.SDK if client.type == CredentialClientInstance.Type.sdk else AuditSource.AGENT
    elif user and getattr(user, 'is_authenticated', False):
        source = AuditSource.SDK if user.__class__.__name__ == 'IntegrationApplication' else AuditSource.ADMINISTRATOR
    else:
        source = AuditSource.JUMPSERVER
    values.setdefault('source', source)
    values.setdefault('operator', (getattr(user, 'name', '') if source == AuditSource.ADMINISTRATOR else source) or source)
    if request:
        values.setdefault('remote_addr', get_request_ip(request) or None)
    with tmp_to_org(obj.org_id):
        return ApplicationAudit.objects.create(event=event, **values)


@dataclass
class ApplicationAuditContext:
    """Explicit hand-off from the API to auditing after the request transaction."""
    event: str
    values: dict
    fetch_identity: list | None = None
    error_code: str = ''
    success_recorded: bool = False

    def set_request_data(self, data):
        self.values.update(
            credential_key=data.get('key', ''),
            instance_id=data.get('instance_id', ''),
            configuration_id=data.get('configuration_id'),
        )

    def set_client(self, client):
        self.values = {'client': client, 'credential_key': self.values.get('credential_key', '')}

    def set_fetch_result(self, revision, success_recorded):
        self.values['revision'] = revision
        self.success_recorded = success_recorded

    def record_failure(self, status_code):
        summary = self.error_code or f'Request rejected (HTTP {status_code}).'
        with transaction.atomic():
            record(self.event, **self.values, result='failed', summary=summary)

    def record_recovery(self):
        if self.success_recorded:
            return
        with transaction.atomic():
            record(self.event, **self.values, result='success', summary='Credential access recovered.')


class CredentialFetchAudit:
    # ponytail: idle states expire after a day; cache loss may add one new failure audit.
    state_timeout = 86400
    lock_timeout = 30

    def __init__(self, context):
        self.context = context
        digest = sha256(json.dumps(context.fetch_identity).encode()).hexdigest()
        self.cache_key = 'credential-fetch-state:' + digest
        self.failure_recorded = False

    def record_result(self, status_code):
        state = None
        if status_code >= 400:
            state = [status_code, self.context.error_code]

        try:
            previous = cache.get(self.cache_key)
            if previous == state:
                if state is not None:
                    cache.touch(self.cache_key, self.state_timeout)
                return

            lock_key = cache.make_key(self.cache_key + ':lock')
            with cache.lock(lock_key, expire=self.lock_timeout):
                previous = cache.get(self.cache_key)
                self.record_transition(previous, state, status_code)
                self.save_state(state)
        except RedisError:
            logger.warning('Credential fetch audit cache unavailable; deduplication skipped.')
            if status_code >= 400 and not self.failure_recorded:
                self.context.record_failure(status_code)

    def record_transition(self, previous, state, status_code):
        if previous == state:
            return
        if state is not None:
            self.context.record_failure(status_code)
            self.failure_recorded = True
            return
        if previous is not None:
            self.context.record_recovery()

    def save_state(self, state):
        if state is None:
            cache.delete(self.cache_key)
            return
        cache.set(self.cache_key, state, self.state_timeout)
