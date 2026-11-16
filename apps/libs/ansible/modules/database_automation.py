#!/usr/bin/python
"""Native database query, connectivity and account automation entry point."""
import contextlib

from ansible.module_utils.basic import AnsibleModule

from libs.ansible.modules_utils.database import (
    DATABASE_TYPES, DatabaseAutomationError, DatabaseClient, safe_error,
)


def main():
    module = AnsibleModule(argument_spec=dict(
        database_type=dict(type='str', required=True, choices=DATABASE_TYPES),
        action=dict(type='str', required=True, choices=(
            'ping', 'query', 'gather_facts', 'gather_accounts',
            'push_account', 'change_secret', 'remove_account',
        )),
        login_host=dict(type='str', required=True),
        login_port=dict(type='int', required=True),
        login_user=dict(type='str', required=True),
        login_password=dict(type='str', required=True, no_log=True),
        login_database=dict(type='str', default=''),
        connect_timeout=dict(type='int', default=15),
        connection_options=dict(type='dict', default={}, options=dict(
            tenant_mode=dict(type='str', choices=('mysql', 'oracle'), default='mysql'),
            use_ssl=dict(type='bool', default=False),
            allow_invalid_cert=dict(type='bool', default=False),
            server_name=dict(type='str'),
            ca_cert=dict(type='str', no_log=True),
            client_cert=dict(type='str', no_log=True),
            client_key=dict(type='str', no_log=True),
            sysdba=dict(type='bool', default=False),
        )),
        query=dict(type='str'),
        max_rows=dict(type='int', default=1000),
        name=dict(type='str'),
        password=dict(type='str', no_log=True),
        secret_type=dict(type='str', default='password', choices=('password',)),
        host=dict(type='str', default='%'),
    ), supports_check_mode=True)
    p = module.params
    action, client = p['action'], None
    sensitive = action in ('push_account', 'change_secret', 'remove_account')
    if module.check_mode and action == 'query':
        module.exit_json(changed=False, skipped=True, msg='SQL is not executed in check mode')
    try:
        client = DatabaseClient(
            p['database_type'], p['login_host'], p['login_port'],
            p['login_user'], p['login_password'], p['login_database'],
            p['connection_options'], p['connect_timeout'],
        )
        if action == 'ping':
            result = client.ping()
        elif action == 'gather_facts':
            result = {'info': client.facts()}
        elif action == 'gather_accounts':
            result = {'info': client.accounts()}
        elif action == 'query':
            result = client.query(p['query'], p['max_rows'])
        else:
            result = client.manage_account(
                action, p['name'], p['password'], p['host'], module.check_mode,
            )
    except ImportError as error:
        # Driver loader errors can contain connection arguments, too.
        dependencies = {'dameng': 'dmPython and its DPI runtime',
                        'db2': 'ibm_db and IBM CLI (Linux x86_64 executor)',
                        'oceanbase': 'PyMySQL', 'clickhouse': 'clickhouse-driver',
                        'oracle': 'oracledb'}
        module.fail_json(changed=bool(client and client.changed),
                         msg='Install {} in the active Ansible execution environment ({})'.format(
                             dependencies[p['database_type']], type(error).__name__),
                         reason_code='DATABASE_DRIVER_UNAVAILABLE')
    except Exception as error:
        module.fail_json(
            changed=bool(client and client.changed),
            msg=safe_error(error, (p['login_password'], p.get('password')), sensitive=sensitive and not isinstance(error, DatabaseAutomationError)),
            reason_code='DATABASE_AUTOMATION_FAILED',
        )
    finally:
        if client:
            with contextlib.suppress(Exception):
                client.close()
    result.setdefault('changed', False)
    module.exit_json(**result)


if __name__ == '__main__':
    main()
