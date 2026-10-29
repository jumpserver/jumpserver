"""Application-owned access materials and policy scope notifications."""
import json
from shlex import quote
from uuid import uuid4

from accounts.const import ApplicationEvent, AuditEvent
from django.template.loader import render_to_string

from .audit import record
from .documentation import agent_build_command, sdk_install_commands, sdk_example
from .events import enqueue


def publish_application_scope(application):
    enqueue(
        record(AuditEvent.CONFIGURATION_UPDATED, application=application),
        ApplicationEvent.APPLICATION_SCOPE_UPDATED,
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
            code = sdk_example(language)
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
        install_command = sdk_install_commands(endpoint)[language]
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
        'version': 1,
        'endpoint': endpoint, 'org_id': str(application.org_id),
        'app_id': str(application.id), 'app_secret': application.secret,
        'socket': {'owner': settings['app_user']},
        'services': [],
    }
    if params['store_scope'] != 'none':
        bootstrap['store'] = {
            'accounts': ['all'] if params['store_scope'] == 'all' else [str(value) for value in params['store_accounts']],
            'root': f'{install_path}/credentials', 'format': params['store_format'], 'owner': settings['app_user'],
        }
    setup = params.get('agent_setup', 'delivery')
    if setup != 'delivery':
        selectors, fields = [], {}
        for account in params['service_accounts']:
            selectors.append({'id': str(account['account_id']),
                              **({'alias': account['alias']} if account['alias'] else {})})
            prefix = f"{account['alias']}." if account['alias'] else ''
            fields[account['username_field']] = prefix + 'username'
            fields[account['secret_field']] = prefix + 'secret'
        service = {
            'name': params['service_name'],
            'accounts': selectors,
            'allow_account_switch': params['allow_account_switch'],
            'update_on_notification': params['update_on_notification'],
            'update_config': {'file': params['config_file'], 'format': params['config_format'], 'fields_map': fields},
        }
        if params['service_action_type'] == 'systemd':
            service['reload_service'] = {'unit': params['systemd_unit'], 'operation': params['systemd_action']}
        elif params['service_action_type'] == 'script':
            service['reload_service'] = {'path': params['service_script']}
        if params['application_check']:
            service['app_check'] = {'path': params['application_check'], 'confirm_on_success': True}
        bootstrap['services'] = [service]
    filename = 'pam-agent.json'
    preparation = f'{agent_build_command(endpoint)} &&\nsudo install -m 0755 ./pam-agent /usr/local/bin/pam-agent'
    installation = (
        f'chmod 0600 {filename} && '
        'sudo /usr/local/bin/pam-agent install '
        f'--bootstrap {filename}'
    )
    foreground_unix = foreground_windows = ''
    if setup == 'delivery':
        short_id = str(application.id).replace('-', '')[:12]
        directory = f'$HOME/.jms-pam-agent/{short_id}'
        foreground_unix = (
            f'# Initialize once\nchmod 0600 {filename}\n'
            f'./pam-agent init-local --bootstrap ./{filename} '
            f'--directory "{directory}"\n'
            f'# Start or restart\n./pam-agent run --local --config "{directory}/agent.json"'
        )
        foreground_windows = (
            f"$agentDir = Join-Path $HOME '.jms-pam-agent\\{short_id}'\n"
            '# Initialize once\n'
            f".\\pam-agent.exe init-local --bootstrap (Join-Path $PWD '{filename}') "
            '--directory $agentDir\n'
            '# Start or restart\n'
            ".\\pam-agent.exe run --local --config (Join-Path $agentDir 'agent.json')"
        )
    return {
        'type': 'agent', 'config': json.dumps(bootstrap, indent=2), 'filename': filename,
        'preparation_command': preparation, 'registration_command': installation,
        'install_command': f'{preparation} &&\n{installation}',
        'foreground_unix_command': foreground_unix,
        'foreground_windows_command': foreground_windows,
        'service_name': 'pam-agent', 'agent_language': 'go',
    }
