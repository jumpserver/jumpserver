#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r'''
---
module: postgresql_login_ping
short_description: Verify PostgreSQL credentials with a minimal query
description:
  - Connects with the supplied credentials and executes C(SELECT 1).
options:
  login_user:
    type: str
    required: true
  login_password:
    type: str
    required: true
  login_host:
    type: str
    required: true
  login_port:
    type: int
    default: 5432
  db:
    type: str
    required: true
  ssl_mode:
    type: str
    default: prefer
  ca_cert:
    type: path
  ssl_cert:
    type: path
  ssl_key:
    type: path
  connect_timeout:
    type: int
    default: 15
requirements:
  - psycopg2
'''

from ansible.module_utils.basic import AnsibleModule

try:
    import psycopg2
    PSYCOPG2_IMPORT_ERROR = None
except ImportError as error:
    psycopg2 = None
    PSYCOPG2_IMPORT_ERROR = error


def main():
    module = AnsibleModule(
        argument_spec=dict(
            login_user=dict(type='str', required=True),
            login_password=dict(type='str', required=True, no_log=True),
            login_host=dict(type='str', required=True),
            login_port=dict(type='int', default=5432),
            db=dict(type='str', required=True),
            ssl_mode=dict(type='str', default='prefer'),
            ca_cert=dict(type='path', default=None),
            ssl_cert=dict(type='path', default=None),
            ssl_key=dict(type='path', default=None, no_log=True),
            connect_timeout=dict(type='int', default=15),
        ),
        supports_check_mode=True,
    )

    if psycopg2 is None:
        module.fail_json(
            msg='psycopg2 is required: %s' % PSYCOPG2_IMPORT_ERROR
        )

    params = dict(
        user=module.params['login_user'],
        password=module.params['login_password'],
        host=module.params['login_host'],
        port=module.params['login_port'],
        dbname=module.params['db'],
        sslmode=module.params['ssl_mode'],
        connect_timeout=module.params['connect_timeout'],
    )
    optional = {
        'sslrootcert': module.params['ca_cert'],
        'sslcert': module.params['ssl_cert'],
        'sslkey': module.params['ssl_key'],
    }
    params.update({key: value for key, value in optional.items() if value})

    connection = None
    cursor = None
    try:
        connection = psycopg2.connect(**params)
        cursor = connection.cursor()
        cursor.execute('SELECT 1')
        row = cursor.fetchone()
        if not row or row[0] != 1:
            module.fail_json(msg='PostgreSQL credential probe returned no result')
    except Exception as error:
        module.fail_json(
            msg='Unable to verify PostgreSQL credentials: %s' % error
        )
    finally:
        if cursor is not None:
            cursor.close()
        if connection is not None:
            connection.close()

    module.exit_json(changed=False, is_available=True)


if __name__ == '__main__':
    main()
