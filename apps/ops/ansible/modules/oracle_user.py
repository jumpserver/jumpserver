#!/usr/bin/python

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = '''
---
module: oracle_user
short_description: Adds or removes a user from a Oracle database
description:
    - Adds or removes a user from a Oracle database.

options:
  authentication_type:
    description:
        - Authentication type of the user(default password)
    required: false
    type: str
    choices: ['external', 'global', 'no_authentication', 'password']
  default_tablespace:
    description:
        - The default tablespace for the user
        - If not provided, the default is used
    required: false
    type: str
  oracle_home:
    description:
        - Define the directory into which all Oracle software is installed.
        - Define ORACLE_HOME environment variable if set.
    type: str
  state:
    description:
      - The database user state.
    default: present
    choices: [absent, present]
    type: str
  update_password:
    default: always
    choices: [always, on_create]
    description:
      - C(always) will always update passwords and cause the module to return changed.
      - C(on_create) will only set the password for newly created users.
    type: str
  temporary_tablespace:
    description:
        - The default temporary tablespace for the user
        - If not provided, the default is used
    required: false
    type: str
  name:
    description:
      - The name of the user to add or remove.
    required: true
    aliases: [user]
    type: str
  password:
    description:
      - The password to use for the user.
    type: str
    aliases: [pass]
    
requirements:
  - "oracledb"
'''

EXAMPLES = '''
- name: Create default tablespace user with name 'jms' and password '123456'.
  oracle_user:
    hostname: "remote server"
    login_database: "helowin"
    login_user: "system"
    login_password: "123456"
    name: "jms"
    password: "123456"

- name: Delete user with name 'jms'.
  oracle_user:
    hostname: "remote server"
    login_database: "helowin"
    login_user: "system"
    login_password: "123456"
    name: "jms"
    state: "absent"
'''

RETURN = '''
name:
    description: The name of the user to add or remove.
    returned: success
    type: str
'''

from ansible.module_utils.basic import AnsibleModule

from ops.ansible.modules_utils.oracle_common import (
    OracleClient, oracle_common_argument_spec
)


def user_find(oracle_client, username):
    user = None
    username = username.upper()
    user_find_sql = "select username, " \
                    "       authentication_type, " \
                    "       default_tablespace, " \
                    "       temporary_tablespace " \
                    "from dba_users where username='%s'" % username
    rtn, err = oracle_client.execute(user_find_sql)
    if isinstance(rtn, dict):
        user = rtn
    return user


def user_add(
        module, oracle_client, username, password, auth_type,
        default_tablespace, temporary_tablespace
):
    username = username.upper()
    extend_sql = None
    user = user_find(oracle_client, username)
    auth_type = auth_type.lower()
    identified_suffix_map = {
        'external': 'identified externally ',
        'global': 'identified globally ',
        'password': 'identified by "%s" ',
    }
    if user:
        user_sql = "alter user %s " % username
        user_sql += identified_suffix_map.get(auth_type, 'no authentication ') % password

        if default_tablespace and default_tablespace.lower() != user['default_tablespace'].lower():
            user_sql += 'default tablespace %s quota unlimited on %s ' % (default_tablespace, default_tablespace)
        if temporary_tablespace and temporary_tablespace.lower() != user['temporary_tablespace'].lower():
            user_sql += 'temporary tablespace %s ' % temporary_tablespace
    else:
        user_sql = "create user %s " % username
        user_sql += identified_suffix_map.get(auth_type, 'no authentication ') % password
        if default_tablespace:
            user_sql += 'default tablespace %s quota unlimited on %s ' % (default_tablespace, default_tablespace)
        if temporary_tablespace:
            user_sql += 'temporary tablespace %s ' % temporary_tablespace
        extend_sql = 'grant connect to %s' % username

    rtn, err = oracle_client.execute(user_sql)
    if err:
        module.fail_json(msg='Cannot add/edit user %s: %s' % (username, err), changed=False)
    else:
        if extend_sql:
            oracle_client.execute(extend_sql)
        module.exit_json(msg='User %s has been created.' % username, changed=True, name=username)


def user_remove(module, oracle_client, username):
    user = user_find(oracle_client, username)

    if user:
        rtn, err = oracle_client.execute('drop user %s cascade' % username)
        if err:
            module.fail_json(msg='Cannot drop user %s: %s' % (username, err), changed=False)
        else:
            module.exit_json(msg='User %s dropped.' % username, changed=True, name=username)
    else:
        module.exit_json(msg="User %s doesn't exist." % username, changed=False, name=username)


# =========================================
# Module execution.
#

def main():
    argument_spec = oracle_common_argument_spec()
    argument_spec.update(
        authentication_type=dict(
            type='str', required=False,
            choices=['external', 'global', 'no_authentication', 'password']
        ),
        default_tablespace=dict(required=False, aliases=['db']),
        name=dict(required=True, aliases=['user']),
        password=dict(aliases=['pass'], no_log=True),
        state=dict(type='str', default='present', choices=['absent', 'present']),
        update_password=dict(default="always", choices=["always", "on_create"], no_log=False),
        temporary_tablespace=dict(type='str', default=None),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    authentication_type = module.params['authentication_type'] or 'password'
    default_tablespace = module.params['default_tablespace']
    user = module.params['name']
    password = module.params['password']
    state = module.params['state']
    update_password = module.params['update_password']
    temporary_tablespace = module.params['temporary_tablespace']

    oracle_client = OracleClient(module)
    if state == 'present':
        if password is None and update_password == 'always':
            module.fail_json(
                msg='password parameter required when adding a user unless update_password is set to on_create'
            )
        user_add(
            module, oracle_client, username=user, password=password,
            auth_type=authentication_type, default_tablespace=default_tablespace,
            temporary_tablespace=temporary_tablespace
        )
    elif state == 'absent':
        user_remove(oracle_client)
    module.exit_json(changed=True, user=user)


if __name__ == '__main__':
    main()
