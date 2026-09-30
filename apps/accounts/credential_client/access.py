"""Application-owned access materials and policy scope notifications."""
import json
from shlex import quote
from uuid import uuid4

from accounts.const import ApplicationEvent, AuditEvent
from django.template.loader import render_to_string

from .audit import record
from .documentation import SDK_INSTALL_COMMANDS, sdk_example
from .events import enqueue


def publish_application_scope(application):
    enqueue(
        record(AuditEvent.CONFIGURATION_UPDATED, application=application),
        ApplicationEvent.CONFIGURATION_UPDATED,
    )


def materials(application, params, endpoint):
    if params['type'] == 'sdk':
        instance_id = uuid4().hex
        language = params.get('sdk_language', 'python')
        if language == 'python':
            config = render_to_string('accounts/credential_client/sdk_config.py.tpl', {
                'endpoint': repr(endpoint), 'app_id': repr(str(application.id)),
                'app_secret': repr(application.secret), 'org_id': repr(str(application.org_id)),
                'instance_id': repr(instance_id),
            })
            filename = 'jms_pam_config.py'
            code = render_to_string('accounts/credential_client/sdk_application_example.py.tpl')
        else:
            values = {
                'JMS_ENDPOINT': endpoint, 'JMS_APP_ID': str(application.id),
                'JMS_APP_SECRET': application.secret, 'JMS_ORG_ID': str(application.org_id),
            }
            config = (
                '# Reuse this file to keep the instance ID stable. Set JMS_INSTANCE_ID to override it.\n'
                + '\n'.join(f'export {name}={quote(value)}' for name, value in values.items()) + '\n'
                + f'export JMS_INSTANCE_ID="${{JMS_INSTANCE_ID:-{instance_id}}}"\n'
            )
            filename = 'jms_pam_config.sh'
            code = sdk_example(language)
            if language == 'node':
                code = code.replace("require('./index')", "require('@jumpserver/pam')")
        install_command = SDK_INSTALL_COMMANDS[language]
        if language == 'python':
            install_command = f'chmod 0600 {filename}\n{install_command}'
        else:
            install_command = f'chmod 0600 {filename}\n. ./{filename}\n{install_command}'
        return {
            'type': 'sdk', 'sdk_language': language,
            'instance_id': instance_id,
            'config': config, 'filename': filename, 'code': code,
            'install_command': install_command,
        }
    settings = {name: params[name] for name in (
        'app_user', 'install_path', 'delivery_mode', 'systemd_unit', 'systemd_action',
    )}
    install_path = settings['install_path'].rstrip('/')
    bootstrap = {
        'endpoint': endpoint, 'org_id': str(application.org_id),
        'app_id': str(application.id), 'app_secret': application.secret,
        'instance_id': '<instance-id>',
        'state_file': '/var/lib/jms-pam-agent/state.json',
        'event_file': '/var/lib/jms-pam-agent/events.jsonl',
        'reconcile_interval': 300,
        'delivery': {
            'delivery_mode': settings['delivery_mode'],
            'delivery_root': f'{install_path}/credentials',
            'socket_path': '/run/jms-pam-agent/agent.sock',
            'app_user': settings['app_user'],
            'systemd_unit': settings['systemd_unit'],
            'systemd_action': settings['systemd_action'],
        },
        'rules': [],
    }
    filename = 'jms_pam_agent.json'
    preparation = 'sudo install -m 0755 ./jms-pam-agent /usr/local/bin/jms-pam-agent'
    installation = (
        f'chmod 0600 {filename} && '
        'sudo /usr/local/bin/jms-pam-agent install '
        f'--bootstrap {filename} --instance-id "$(hostname)"'
    )
    foreground_unix = foreground_windows = ''
    if settings['delivery_mode'] != 'environment':
        short_id = str(application.id).replace('-', '')[:12]
        directory = f'$HOME/.jms-pam-agent/{short_id}'
        foreground_unix = (
            f'# Initialize once\nchmod 0600 {filename}\n'
            f'./jms-pam-agent init-local --bootstrap ./{filename} '
            f'--directory "{directory}" --instance-id "$(hostname)"\n'
            f'# Start or restart\n./jms-pam-agent run --local --config "{directory}/agent.json"'
        )
        foreground_windows = (
            f"$agentDir = Join-Path $HOME '.jms-pam-agent\\{short_id}'\n"
            '# Initialize once\n'
            f".\\jms-pam-agent.exe init-local --bootstrap (Join-Path $PWD '{filename}') "
            '--directory $agentDir --instance-id $env:COMPUTERNAME\n'
            '# Start or restart\n'
            ".\\jms-pam-agent.exe run --local --config (Join-Path $agentDir 'agent.json')"
        )
    return {
        'type': 'agent', 'config': json.dumps(bootstrap, indent=2), 'filename': filename,
        'preparation_command': preparation, 'registration_command': installation,
        'install_command': f'{preparation} && {installation}',
        'foreground_unix_command': foreground_unix,
        'foreground_windows_command': foreground_windows,
        'service_name': 'jms-pam-agent', 'agent_language': 'go',
    }
