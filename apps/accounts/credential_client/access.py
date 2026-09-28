"""Application-owned access materials and automatic client subscription scopes."""
import hashlib
import json
import shlex

from django.db import transaction
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import PermissionDenied

from accounts.models import ClientAccessConfiguration
from accounts.const import AuditEvent, ApplicationEvent
from accounts.credential_rotation.participants import enroll_client
from .audit import record
from .events import enqueue

AUTOMATIC_SCOPE_PREFIX = 'application-access-'


@transaction.atomic
def refresh_application_scopes(application):
    credentials = list(application.application_credentials.order_by('id'))
    for scope in application.access_configurations.filter(name__startswith=AUTOMATIC_SCOPE_PREFIX):
        if set(scope.credentials.values_list('id', flat=True)) == {item.id for item in credentials}:
            continue
        scope.credentials.set(credentials)
        if scope.is_active and application.is_active:
            for client in scope.instances.filter(is_active=True):
                enroll_client(client)
        enqueue(
            record(AuditEvent.CONFIGURATION_UPDATED, configuration=scope),
            ApplicationEvent.CONFIGURATION_UPDATED,
        )


@transaction.atomic
def subscription_scope(application, access_type='sdk', **settings):
    if not application.is_active:
        raise PermissionDenied(_('The application is disabled.'))
    payload = {'type': access_type, **settings}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:24]
    # The scope stores deployment settings; policies always follow application bindings.
    scope, _created = ClientAccessConfiguration.objects.get_or_create(
        application=application, name=f'{AUTOMATIC_SCOPE_PREFIX}{access_type}-{digest}',
        defaults={'type': access_type, **settings, 'org_id': application.org_id},
    )
    if not scope.is_active:
        raise PermissionDenied(_('The client access configuration is disabled.'))
    scope.credentials.set(application.application_credentials.order_by('id'))
    return scope


def materials(application, params, endpoint):
    if params['type'] == 'sdk':
        config = render_to_string('accounts/credential_client/sdk_config.py.tpl', {
            'endpoint': repr(endpoint), 'app_id': repr(str(application.id)),
            'app_secret': repr(application.secret), 'org_id': repr(str(application.org_id)),
        })
        return {
            'type': 'sdk', 'config': config, 'filename': 'jms_pam_config.py',
            'code': render_to_string('accounts/credential_client/sdk_application_example.py.tpl'),
            'install_command': 'python3 -m pip install --upgrade jms-pam',
        }
    settings = {name: params[name] for name in (
        'app_user', 'install_path', 'delivery_mode', 'systemd_unit', 'systemd_action',
    )}
    scope = subscription_scope(application, 'agent', **settings)
    bootstrap = {
        'endpoint': endpoint, 'org_id': str(application.org_id),
        'app_id': str(application.id), 'app_secret': application.secret,
        'configuration_id': str(scope.id),
        'app_user': scope.app_user, 'install_path': scope.install_path,
    }
    root = scope.install_path.rstrip('/')
    filename = 'jms_pam_agent.json'
    preparation = (
        f'sudo python3 -m venv {shlex.quote(root + "/venv")} && '
        f'sudo {shlex.quote(root + "/venv/bin/pip")} install --upgrade jms-pam'
    )
    installation = (
        f'sudo {shlex.quote(root + "/venv/bin/jms-pam-agent")} install '
        f'--bootstrap {filename} --instance-id "$(hostname)"'
    )
    return {
        'type': 'agent', 'config': json.dumps(bootstrap, indent=2), 'filename': filename,
        'preparation_command': preparation, 'registration_command': installation,
        'install_command': f'{preparation} && {installation}',
    }
