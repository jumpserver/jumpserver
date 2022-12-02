#!/usr/bin/python

# Modified from ansible_collections.community.mongodb.plugins.modules.mongodb_user

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = '''
---
module: mongodb_user
short_description: Adds or removes a user from a MongoDB database
description:
    - Adds or removes a user from a MongoDB database.
version_added: "1.0.0"

extends_documentation_fragment:
  - community.mongodb.login_options
  - community.mongodb.ssl_options

options:
  replica_set:
    description:
      - Replica set to connect to (automatically connects to primary for writes).
    type: str
  database:
    description:
      - The name of the database to add/remove the user from.
    required: true
    type: str
    aliases: [db]
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
  roles:
    type: list
    elements: raw
    description:
      - >
          The database user roles valid values could either be one or more of the following strings:
          'read', 'readWrite', 'dbAdmin', 'userAdmin', 'clusterAdmin', 'readAnyDatabase', 'readWriteAnyDatabase', 'userAdminAnyDatabase',
          'dbAdminAnyDatabase'
      - "Or the following dictionary '{ db: DATABASE_NAME, role: ROLE_NAME }'."
      - "This param requires pymongo 2.5+. If it is a string, mongodb 2.4+ is also required. If it is a dictionary, mongo 2.6+ is required."
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
      - This must be C(always) to use the localhost exception when adding the first admin user.
      - This option is effectively ignored when using x.509 certs. It is defaulted to 'on_create' to maintain a \
          a specific module behaviour when the login_database is '$external'.
    type: str
  create_for_localhost_exception:
    type: path
    description:
      - This is parmeter is only useful for handling special treatment around the localhost exception.
      - If C(login_user) is defined, then the localhost exception is not active and this parameter has no effect.
      - If this file is NOT present (and C(login_user) is not defined), then touch this file after successfully adding the user.
      - If this file is present (and C(login_user) is not defined), then skip this task.

notes:
    - Requires the pymongo Python package on the remote host, version 2.4.2+. This
      can be installed using pip or the OS package manager. Newer mongo server versions require newer
      pymongo versions. @see http://api.mongodb.org/python/current/installation.html
requirements:
  - "pymongo"
author:
    - "Elliott Foster (@elliotttf)"
    - "Julien Thebault (@Lujeni)"
'''

EXAMPLES = '''
- name: Create 'burgers' database user with name 'bob' and password '12345'.
  community.mongodb.mongodb_user:
    database: burgers
    name: bob
    password: 12345
    state: present

- name: Create a database user via SSL (MongoDB must be compiled with the SSL option and configured properly)
  community.mongodb.mongodb_user:
    database: burgers
    name: bob
    password: 12345
    state: present
    ssl: True

- name: Delete 'burgers' database user with name 'bob'.
  community.mongodb.mongodb_user:
    database: burgers
    name: bob
    state: absent

- name: Define more users with various specific roles (if not defined, no roles is assigned, and the user will be added via pre mongo 2.2 style)
  community.mongodb.mongodb_user:
    database: burgers
    name: ben
    password: 12345
    roles: read
    state: present

- name: Define roles
  community.mongodb.mongodb_user:
    database: burgers
    name: jim
    password: 12345
    roles: readWrite,dbAdmin,userAdmin
    state: present

- name: Define roles
  community.mongodb.mongodb_user:
    database: burgers
    name: joe
    password: 12345
    roles: readWriteAnyDatabase
    state: present

- name: Add a user to database in a replica set, the primary server is automatically discovered and written to
  community.mongodb.mongodb_user:
    database: burgers
    name: bob
    replica_set: belcher
    password: 12345
    roles: readWriteAnyDatabase
    state: present

# add a user 'oplog_reader' with read only access to the 'local' database on the replica_set 'belcher'. This is useful for oplog access (MONGO_OPLOG_URL).
# please notice the credentials must be added to the 'admin' database because the 'local' database is not synchronized and can't receive user credentials
# To login with such user, the connection string should be MONGO_OPLOG_URL="mongodb://oplog_reader:oplog_reader_password@server1,server2/local?authSource=admin"
# This syntax requires mongodb 2.6+ and pymongo 2.5+
- name: Roles as a dictionary
  community.mongodb.mongodb_user:
    login_user: root
    login_password: root_password
    database: admin
    user: oplog_reader
    password: oplog_reader_password
    state: present
    replica_set: belcher
    roles:
      - db: local
        role: read

- name: Adding a user with X.509 Member Authentication
  community.mongodb.mongodb_user:
    login_host: "mongodb-host.test"
    login_port: 27001
    login_database: "$external"
    database: "admin"
    name: "admin"
    password: "test"
    roles:
    - dbAdminAnyDatabase
    ssl: true
    ssl_ca_certs: "/tmp/ca.crt"
    ssl_certfile: "/tmp/tls.key" #cert and key in one file
    state: present
    auth_mechanism: "MONGODB-X509"
    connection_options:
     - "tlsAllowInvalidHostnames=true"
'''

RETURN = '''
user:
    description: The name of the user to add or remove.
    returned: success
    type: str
'''

import os
import traceback
from operator import itemgetter


from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import binary_type, text_type
from ansible.module_utils._text import to_native, to_bytes
from ansible_collections.community.mongodb.plugins.module_utils.mongodb_common import (
    missing_required_lib,
    mongodb_common_argument_spec,
    mongo_auth,
    PYMONGO_IMP_ERR,
    pymongo_found,
    get_mongodb_client,
)


def user_find(client, user, db_name):
    """Check if the user exists.

    Args:
        client (cursor): Mongodb cursor on admin database.
        user (str): User to check.
        db_name (str): User's database.

    Returns:
        dict: when user exists, False otherwise.
    """
    try:
        for mongo_user in client[db_name].command('usersInfo')['users']:
            if mongo_user['user'] == user:
                # NOTE: there is no 'db' field in mongo 2.4.
                if 'db' not in mongo_user:
                    return mongo_user
                # Workaround to make the condition works with AWS DocumentDB,
                # since all users are in the admin database.
                if mongo_user["db"] in [db_name, "admin"]:
                    return mongo_user
    except Exception as excep:
        if hasattr(excep, 'code') and excep.code == 11:  # 11=UserNotFound
            pass  # Allow return False
        else:
            raise
    return False


def user_add(module, client, db_name, user, password, roles):
    # pymongo's user_add is a _create_or_update_user so we won't know if it was changed or updated
    # without reproducing a lot of the logic in database.py of pymongo
    db = client[db_name]

    try:
        exists = user_find(client, user, db_name)
    except Exception as excep:
        # We get this exception: "not authorized on admin to execute command"
        # when auth is enabled on a new instance. The loalhost exception should
        # allow us to create the first user. If the localhost exception does not apply,
        # then user creation will also fail with unauthorized. So, ignore Unauthorized here.
        if hasattr(excep, 'code') and excep.code == 13:  # 13=Unauthorized
            exists = False
        else:
            raise

    if exists:
        user_add_db_command = 'updateUser'
        if not roles:
            roles = None
    else:
        user_add_db_command = 'createUser'

    user_dict = {}

    if password is not None:
        user_dict["pwd"] = password
    if roles is not None:
        user_dict["roles"] = roles

    db.command(user_add_db_command, user, **user_dict)


def user_remove(module, client, db_name, user):
    exists = user_find(client, user, db_name)
    if exists:
        if module.check_mode:
            module.exit_json(changed=True, user=user)
        db = client[db_name]
        db.command("dropUser", user)
    else:
        module.exit_json(changed=False, user=user)


def check_if_roles_changed(uinfo, roles, db_name):
    # We must be aware of users which can read the oplog on a replicaset
    # Such users must have access to the local DB, but since this DB does not store users credentials
    # and is not synchronized among replica sets, the user must be stored on the admin db
    # Therefore their structure is the following :
    # {
    #     "_id" : "admin.oplog_reader",
    #     "user" : "oplog_reader",
    #     "db" : "admin",                    # <-- admin DB
    #     "roles" : [
    #         {
    #             "role" : "read",
    #             "db" : "local"             # <-- local DB
    #         }
    #     ]
    # }

    def make_sure_roles_are_a_list_of_dict(roles, db_name):
        output = list()
        for role in roles:
            if isinstance(role, (binary_type, text_type)):
                new_role = {"role": role, "db": db_name}
                output.append(new_role)
            else:
                output.append(role)
        return output

    roles_as_list_of_dict = make_sure_roles_are_a_list_of_dict(roles, db_name)
    uinfo_roles = uinfo.get('roles', [])

    if sorted(roles_as_list_of_dict, key=itemgetter('db')) == sorted(uinfo_roles, key=itemgetter('db')):
        return False
    return True


# =========================================
# Module execution.
#

def main():
    argument_spec = mongodb_common_argument_spec()
    argument_spec.update(
        database=dict(required=True, aliases=['db']),
        name=dict(required=True, aliases=['user']),
        password=dict(aliases=['pass'], no_log=True),
        replica_set=dict(default=None),
        roles=dict(default=None, type='list', elements='raw'),
        state=dict(default='present', choices=['absent', 'present']),
        update_password=dict(default="always", choices=["always", "on_create"], no_log=False),
        create_for_localhost_exception=dict(default=None, type='path'),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )
    login_user = module.params['login_user']

    # Certs don't have a password but we want this module behaviour
    if module.params['login_database'] == '$external':
        module.params['update_password'] = 'on_create'

    if not pymongo_found:
        module.fail_json(msg=missing_required_lib('pymongo'),
                         exception=PYMONGO_IMP_ERR)

    create_for_localhost_exception = module.params['create_for_localhost_exception']
    b_create_for_localhost_exception = (
        to_bytes(create_for_localhost_exception, errors='surrogate_or_strict')
        if create_for_localhost_exception is not None else None
    )

    db_name = module.params['database']
    user = module.params['name']
    password = module.params['password']
    roles = module.params['roles'] or []
    state = module.params['state']
    update_password = module.params['update_password']

    try:
        directConnection = False
        if module.params['replica_set'] is None:
            directConnection = True
        client = get_mongodb_client(module, directConnection=directConnection)
        client = mongo_auth(module, client, directConnection=directConnection)
    except Exception as e:
        module.fail_json(msg='Unable to connect to database: %s' % to_native(e))

    if state == 'present':
        if password is None and update_password == 'always':
            module.fail_json(msg='password parameter required when adding a user unless update_password is set to on_create')

        if login_user is None and create_for_localhost_exception is not None:
            if os.path.exists(b_create_for_localhost_exception):
                try:
                    client.close()
                except Exception:
                    pass
                module.exit_json(changed=False, user=user, skipped=True, msg="The path in create_for_localhost_exception exists.")

        try:
            if update_password != 'always':
                uinfo = user_find(client, user, db_name)
                if uinfo:
                    password = None
                    if not check_if_roles_changed(uinfo, roles, db_name):
                        module.exit_json(changed=False, user=user)

            if module.check_mode:
                module.exit_json(changed=True, user=user)
            user_add(module, client, db_name, user, password, roles)
        except Exception as e:
            module.fail_json(msg='Unable to add or update user: %s' % to_native(e), exception=traceback.format_exc())
        finally:
            try:
                client.close()
            except Exception:
                pass
            # Here we can  check password change if mongo provide a query for that : https://jira.mongodb.org/browse/SERVER-22848
            # newuinfo = user_find(client, user, db_name)
            # if uinfo['role'] == newuinfo['role'] and CheckPasswordHere:
            #    module.exit_json(changed=False, user=user)

        if login_user is None and create_for_localhost_exception is not None:
            # localhost exception applied.
            try:
                # touch the file
                open(b_create_for_localhost_exception, 'wb').close()
            except Exception as e:
                module.fail_json(
                    changed=True,
                    msg='Added user but unable to touch create_for_localhost_exception file %s: %s' % (create_for_localhost_exception, to_native(e)),
                    exception=traceback.format_exc()
                )

    elif state == 'absent':
        try:
            user_remove(module, client, db_name, user)
        except Exception as e:
            module.fail_json(msg='Unable to remove user: %s' % to_native(e), exception=traceback.format_exc())
        finally:
            try:
                client.close()
            except Exception:
                pass
    module.exit_json(changed=True, user=user)


if __name__ == '__main__':
    main()
