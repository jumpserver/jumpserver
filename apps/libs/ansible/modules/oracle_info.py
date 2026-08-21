#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r'''
---
module: oracle_info
short_description: Gather information about Oracle servers
description:
- Gathers information about Oracle servers.

options:
  filter:
    description:
    - Limit the collected information by comma separated string or YAML list.
    - Allowable values are C(version), C(databases), C(settings), C(users).
    - By default, collects all subsets.
    - You can use '!' before value (for example, C(!users)) to exclude it from the information.
    - If you pass including and excluding values to the filter, for example, I(filter=!settings,version),
      the excluding values, C(!settings) in this case, will be ignored.
    type: list
    elements: str
  login_db:
    description:
    - Database name to connect to.
    - It makes sense if I(login_user) is allowed to connect to a specific database only.
    type: str
  exclude_fields:
    description:
    - List of fields which are not needed to collect.
    - "Supports elements: C(db_size). Unsupported elements will be ignored."
    type: list
    elements: str
'''

EXAMPLES = r'''
- name: Get Oracle version with non-default credentials
  oracle_info:
    login_user: mysuperuser
    login_password: mysuperpass
    login_database: service_name
    filter: version

- name: Collect all info except settings and users by sys
  oracle_info:
    login_user: sys
    login_password: sys_pass
    login_database: service_name
    filter: "!settings,!users"
    exclude_fields: db_size
'''

RETURN = r'''
version:
  description: Database server version.
  returned: if not excluded by filter
  type: dict
  sample: { "version": {"full": "11.2.0.1.0"} }
  contains:
    full:
      description: Full server version.
      returned: if not excluded by filter
      type: str
      sample: "11.2.0.1.0"
databases:
  description: Information about databases.
  returned: if not excluded by filter
  type: dict
  sample:
  - { "USERS": { "size": 5242880 }, "EXAMPLE": { "size": 104857600 } }
  contains:
    size:
      description: Database size in bytes.
      returned: if not excluded by filter
      type: dict
      sample: { 'size': 656594 }
settings:
  description: Global settings (variables) information.
  returned: if not excluded by filter
  type: dict
  sample:
  - { "result_cache_mode": "MANUAL", "instance_type": "RDBMS" }
users:
  description: Users information.
  returned: if not excluded by filter
  type: dict
  sample:
  - { "USERS": { "TEST": { "USERNAME": "TEST", "ACCOUNT_STATUS": "OPEN" } } }
'''

from ansible.module_utils.basic import AnsibleModule

from libs.ansible.modules_utils.oracle_common import (
    OracleClient, oracle_common_argument_spec
)


class OracleInfo(object):
    def __init__(self, module, oracle_client):
        self.module = module
        self.oracle_client = oracle_client
        self.info = {
            'version': {}, 'databases': {},
            'settings': {}, 'users': {},
        }

    def get_info(self, filter_, exclude_fields):
        include_list = []
        exclude_list = []

        if filter_:
            partial_info = {}

            for fi in filter_:
                if fi.lstrip('!') not in self.info:
                    self.module.warn('filter element: %s is not allowable, ignored' % fi)
                    continue

                if fi[0] == '!':
                    exclude_list.append(fi.lstrip('!'))
                else:
                    include_list.append(fi)

            if include_list:
                self.__collect(exclude_fields, set(include_list))

                for i in self.info:
                    if i in include_list:
                        partial_info[i] = self.info[i]
            else:
                not_in_exclude_list = list(set(self.info) - set(exclude_list))
                self.__collect(exclude_fields, set(not_in_exclude_list))

                for i in self.info:
                    if i not in exclude_list:
                        partial_info[i] = self.info[i]
            return partial_info
        else:
            self.__collect(exclude_fields, set(self.info))
            return self.info

    def __collect(self, exclude_fields, wanted):
        """Collect all possible subsets."""
        if 'version' in wanted:
            self.__get_version()

        if 'settings' in wanted:
            self.__get_settings()

        if 'databases' in wanted:
            self.__get_databases(exclude_fields)
        #
        if 'users' in wanted:
            self.__get_users()

    def __get_version(self):
        self.info['version'] = {
            'full': self.oracle_client.server_version or ''
        }

    def __get_settings(self):
        """Get global variables (instance settings)."""

        def _set_settings_value(item_dict):
            try:
                self.info['settings'][item_dict['name']] = item_dict['value']
            except KeyError:
                pass

        settings_sql = "SELECT name, value FROM V$PARAMETER"
        rtn, err = self.oracle_client.execute(settings_sql, exception_to_fail=True)

        if isinstance(rtn, dict):
            _set_settings_value(rtn)
        elif isinstance(rtn, list):
            for i in rtn:
                _set_settings_value(i)

    def __get_users(self):
        """Get user info."""
        column_sql = """
            SELECT COLUMN_NAME
            FROM ALL_TAB_COLUMNS
            WHERE OWNER = 'SYS'
              AND TABLE_NAME = 'DBA_USERS'
        """
        available, _ = self.oracle_client.execute(
            column_sql, exception_to_fail=True
        )
        if isinstance(available, dict):
            available = [available]
        available_columns = {
            row['column_name'].lower() for row in (available or [])
        }
        wanted_columns = [
            'username', 'user_id', 'account_status', 'expiry_date',
            'default_tablespace', 'created', 'authentication_type',
            'last_login', 'password_change_date',
        ]
        selected_columns = [
            column for column in wanted_columns
            if column in available_columns
        ]
        required_columns = {'username', 'default_tablespace'}
        if not required_columns.issubset(selected_columns):
            self.module.fail_json(
                msg='DBA_USERS does not expose the required account columns'
            )

        users_sql = 'SELECT {} FROM DBA_USERS'.format(
            ', '.join(selected_columns)
        )
        users, _ = self.oracle_client.execute(
            users_sql, exception_to_fail=True
        )
        if isinstance(users, dict):
            users = [users]

        roles_sql = """
            SELECT RP.GRANTEE, RP.GRANTED_ROLE
            FROM DBA_ROLE_PRIVS RP
            JOIN DBA_USERS U ON U.USERNAME = RP.GRANTEE
        """
        roles, roles_error = self.oracle_client.execute(roles_sql)
        if roles_error:
            self.module.warn(
                'Unable to collect Oracle role memberships: %s'
                % roles_error
            )
            roles = []
        if isinstance(roles, dict):
            roles = [roles]

        privileges_sql = """
            SELECT SP.GRANTEE, SP.PRIVILEGE
            FROM DBA_SYS_PRIVS SP
            JOIN DBA_USERS U ON U.USERNAME = SP.GRANTEE
        """
        privileges, privileges_error = self.oracle_client.execute(
            privileges_sql
        )
        if privileges_error:
            self.module.warn(
                'Unable to collect Oracle system privileges: %s'
                % privileges_error
            )
            privileges = []
        if isinstance(privileges, dict):
            privileges = [privileges]

        roles_by_user = {}
        for role in roles or []:
            roles_by_user.setdefault(role['grantee'], []).append(
                role['granted_role']
            )
        privileges_by_user = {}
        for privilege in privileges or []:
            privileges_by_user.setdefault(
                privilege['grantee'], []
            ).append(privilege['privilege'])

        for item in users or []:
            item = dict(item)
            tablespace = item.pop('default_tablespace')
            username = item.pop('username')
            item['roles'] = roles_by_user.get(username, [])
            item['privileges'] = privileges_by_user.get(username, [])
            self.info['users'].setdefault(tablespace, {})[username] = item

    def __get_databases(self, exclude_fields):
        """Get info about databases."""

        def _set_databases_value(item_dict):
            try:
                tablespace_name = item_dict.pop('tablespace_name')
                size = item_dict.get('size')
                partial_params = {}
                if size:
                    partial_params['size'] = size
                self.info['databases'][tablespace_name] = partial_params
            except KeyError:
                pass

        database_sql = 'SELECT ' \
                       '      tablespace_name, sum(bytes) as "size"' \
                       'FROM dba_data_files GROUP BY tablespace_name'
        if exclude_fields and 'db_size' in exclude_fields:
            database_sql = "SELECT " \
                           "      tablespace_name " \
                           "FROM dba_data_files GROUP BY tablespace_name"

        rtn, err = self.oracle_client.execute(database_sql, exception_to_fail=True)
        if isinstance(rtn, dict):
            _set_databases_value(rtn)
        elif isinstance(rtn, list):
            for i in rtn:
                _set_databases_value(i)


# ===========================================
# Module execution.
#


def main():
    argument_spec = oracle_common_argument_spec()
    argument_spec.update(
        filter=dict(type='list'),
        exclude_fields=dict(type='list'),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    filter_ = module.params['filter']
    exclude_fields = module.params['exclude_fields']

    if filter_:
        filter_ = [f.strip() for f in filter_]

    if exclude_fields:
        exclude_fields = set([f.strip() for f in exclude_fields])

    oracle_client = OracleClient(module)
    try:
        oracle = OracleInfo(module, oracle_client)
        info = oracle.get_info(filter_, exclude_fields)
    finally:
        oracle_client.close()

    module.exit_json(changed=False, **info)


if __name__ == '__main__':
    main()
