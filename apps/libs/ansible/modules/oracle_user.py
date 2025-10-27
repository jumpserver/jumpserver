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
changed:
    description: Whether the user was modified.
    returned: success
    type: bool
'''
import re

from ansible.module_utils.basic import AnsibleModule

from libs.ansible.modules_utils.oracle_common import (
    OracleClient, oracle_common_argument_spec
)


def validate_identifier(name):
    """
    Strictly validate Oracle identifiers (usernames, tablespace names)
    Only letters, numbers, and underscores are allowed.
    The length must be ≤ 30 characters, and the first character must be a letter.
    """
    if not name:
        return False, "Identifier cannot be empty"
    if len(name) > 30:
        return False, "Identifier must be at most 30 characters"
    if not re.match(r'^(C##|c##)?[A-Za-z][A-Za-z0-9_]*$', name):
        msg = ("Identifier can only contain letters, numbers, "
               "and underscores (must start with a letter)")
        return False, msg
    return True, ""


def user_find(oracle_client, username):
    user_find_sql = """
        SELECT username, 
               authentication_type, 
               default_tablespace, 
               temporary_tablespace 
        FROM dba_users 
        WHERE username = UPPER(:username)
    """
    rtn, err = oracle_client.execute(user_find_sql, {'username': username})
    if err:
        return None, err
    if isinstance(rtn, list) and len(rtn) > 0:
        return rtn[0], None
    return rtn, None


def get_identified_clause(auth_type, password):
    auth_type = auth_type.lower()
    if auth_type == 'external':
        return "IDENTIFIED EXTERNALLY"
    elif auth_type == 'global':
        return "IDENTIFIED GLOBALLY"
    elif auth_type == 'no_authentication':
        return "IDENTIFIED BY VALUES ''"
    elif auth_type == 'password':
        if not password:
            raise ValueError("Password is required for 'password' authentication type")
        quote_password = password.replace('"', '""')
        return f'IDENTIFIED BY "{quote_password}"'
    else:
        raise ValueError(f"Unsupported authentication type: {auth_type}")


def user_add(
        module, oracle_client, username, password, auth_type,
        default_tablespace, temporary_tablespace, update_password
):
    valid, msg = validate_identifier(username)
    if not valid:
        module.fail_json(msg=f"Invalid username: {msg}")

    if default_tablespace:
        valid, msg = validate_identifier(default_tablespace)
        if not valid:
            module.fail_json(msg=f"Invalid default tablespace: {msg}")
        default_tablespace = default_tablespace.upper()

    if temporary_tablespace:
        valid, msg = validate_identifier(temporary_tablespace)
        if not valid:
            module.fail_json(msg=f"Invalid temporary tablespace: {msg}")
        temporary_tablespace = temporary_tablespace.upper()

    user, err = user_find(oracle_client, username)
    if err:
        module.fail_json(msg=f"Failed to check user existence: {err}")

    desired_attrs = {
        'auth_type': auth_type.lower(),
        'default_tablespace': default_tablespace,
        'temporary_tablespace': temporary_tablespace,
    }
    username = username.upper()
    if user:
        current_attrs = {
            'auth_type': user['authentication_type'].lower(),
            'default_tablespace': user['default_tablespace'],
            'temporary_tablespace': user['temporary_tablespace']
        }
        need_change = False
        if current_attrs['auth_type'] != desired_attrs['auth_type']:
            need_change = True
        if (desired_attrs['default_tablespace'] and
                current_attrs['default_tablespace'] != desired_attrs['default_tablespace']):
            need_change = True
        if (desired_attrs['temporary_tablespace'] and
                current_attrs['temporary_tablespace'] != desired_attrs['temporary_tablespace']):
            need_change = True
        if desired_attrs['auth_type'] == 'password' and update_password == 'always':
            need_change = True
        if not need_change:
            module.exit_json(changed=False, name=username)

        sql_parts = [f"ALTER USER {username}"]
        identified_clause = get_identified_clause(auth_type, password)
        sql_parts.append(identified_clause)

        if (desired_attrs['default_tablespace'] and
                current_attrs['default_tablespace'] != desired_attrs['default_tablespace']):
            sql_parts.append(f"DEFAULT TABLESPACE {desired_attrs['default_tablespace']}")
            sql_parts.append(f"QUOTA UNLIMITED ON {desired_attrs['default_tablespace']}")

        if (desired_attrs['temporary_tablespace'] and
                current_attrs['temporary_tablespace'] != desired_attrs['temporary_tablespace']):
            sql_parts.append(f"TEMPORARY TABLESPACE {desired_attrs['temporary_tablespace']}")
        user_sql = " ".join(sql_parts)
    else:
        sql_parts = [f"CREATE USER {username}"]
        identified_clause = get_identified_clause(auth_type, password)
        sql_parts.append(identified_clause)

        if desired_attrs['default_tablespace']:
            sql_parts.append(f"DEFAULT TABLESPACE {desired_attrs['default_tablespace']}")
            sql_parts.append(f"QUOTA UNLIMITED ON {desired_attrs['default_tablespace']}")

        if desired_attrs['temporary_tablespace']:
            sql_parts.append(f"TEMPORARY TABLESPACE {desired_attrs['temporary_tablespace']}")
        user_sql = " ".join(sql_parts)

    try:
        ret, err = oracle_client.execute(user_sql)
        if err:
            module.fail_json(msg=f"Failed to modify user {username}: {err}", changed=False)
        oracle_client.commit()
    except Exception as e:
        module.fail_json(msg=f"Database error while modifying user {username}: {str(e)}", changed=False)
        
    try:
        ret, err = oracle_client.execute(f'GRANT CREATE SESSION TO {username}')
        if err:
            module.fail_json(msg=f"Failed to grant create session to {username}: {err}", changed=False)
        action = 'updated' if user else 'created'
        module.exit_json(changed=True, name=username, msg=f"User {username} {action} successfully")
    except Exception as e:
        module.fail_json(msg=f"Database error while modifying user {username}: {str(e)}", changed=False)


def user_remove(module, oracle_client, username):
    black_list = ['sys','system','dbsnmp']
    if username.lower() in black_list:
       module.fail_json(msg=f'Trying to drop an internal user: %s. Not allowed' % username)

    user, err = user_find(oracle_client, username)
    if err:
        module.fail_json(msg=f"Failed to check user existence: {err}")

    if not user:
        module.exit_json(changed=False, name=username, msg=f"User {username} does not exist")

    drop_sql = f"DROP USER {username.upper()} CASCADE"
    try:
        _, err = oracle_client.execute(drop_sql)
        if err:
            module.fail_json(msg=f"Failed to drop user {username}: {err}", changed=False)
        module.exit_json(changed=True, name=username, msg=f"User {username} dropped successfully")
    except Exception as e:
        module.fail_json(msg=f"Database error while dropping user {username}: {str(e)}", changed=False)


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
        supports_check_mode=False,
    )

    authentication_type = module.params['authentication_type'] or 'password'
    default_tablespace = module.params['default_tablespace']
    user = module.params['name']
    password = module.params['password']
    state = module.params['state']
    update_password = module.params['update_password']
    temporary_tablespace = module.params['temporary_tablespace']

    try:
        oracle_client = OracleClient(module)
    except Exception as e:
        module.fail_json(msg=f"Failed to connect to Oracle: {str(e)}")
        return

    if state == 'present':
        if not password and update_password == 'always':
            module.fail_json(
                msg='password parameter required when adding a user unless update_password is set to on_create'
            )
        user_add(
            module, oracle_client, username=user, password=password,
            auth_type=authentication_type, default_tablespace=default_tablespace,
            temporary_tablespace=temporary_tablespace, update_password=update_password
        )
    elif state == 'absent':
        user_remove(module, oracle_client, user)
    module.exit_json(changed=True, user=user)


if __name__ == '__main__':
    main()
