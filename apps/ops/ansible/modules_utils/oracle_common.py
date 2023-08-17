import os

import oracledb

from oracledb.exceptions import DatabaseError
from ansible.module_utils._text import to_native


def oracle_common_argument_spec():
    """
    Returns a dict containing common options shared across the Oracle modules.
    """
    options = dict(
        login_user=dict(type='str', required=False),
        login_password=dict(type='str', required=False, no_log=True),
        login_database=dict(type='str', required=False, default='test'),
        login_host=dict(type='str', required=False, default='localhost'),
        login_port=dict(type='int', required=False, default=1521),
        oracle_home=dict(type='str', required=False),
        mode=dict(type='str', required=False),
    )
    return options


class OracleClient(object):
    def __init__(self, module):
        self.module = module
        self._conn = None
        self._cursor = None
        self.connect_params = {}

        self.init_params()

    def init_params(self):
        params = self.module.params
        hostname = params['login_host']
        port = params['login_port']
        service_name = params['login_database']
        username = params['login_user']
        password = params['login_password']
        oracle_home = params['oracle_home']
        mode = params['mode']

        if oracle_home:
            os.environ.setdefault('ORACLE_HOME', oracle_home)
        if mode == 'sysdba':
            self.connect_params['mode'] = oracledb.SYSDBA

        self.connect_params['host'] = hostname
        self.connect_params['port'] = port
        self.connect_params['user'] = username
        self.connect_params['password'] = password
        self.connect_params['service_name'] = service_name

    @property
    def cursor(self):
        if self._cursor is None:
            try:
                # oracledb.init_oracle_client(lib_dir='/opt/oracle/instantclient_19_10')
                self._conn = oracledb.connect(**self.connect_params)
                self._cursor = self._conn.cursor()
            except DatabaseError as err:
                self.module.fail_json(
                    msg="Unable to connect to database: %s, %s" % (to_native(err), self.connect_params)
                )
        return self._cursor

    def execute(self, sql, exception_to_fail=False):
        sql = sql[:-1] if sql.endswith(';') else sql
        result, error = None, None
        try:
            self.cursor.execute(sql)
            sql_header = self.cursor.description or []
            column_names = [description[0].lower() for description in sql_header]
            if column_names:
                result = [dict(zip(column_names, row)) for row in self.cursor]
                result = result[0] if len(result) == 1 else result
            else:
                result = None
        except DatabaseError as err:
            error = err
        if exception_to_fail and error:
            self.module.fail_json(msg='Cannot execute sql: %s' % to_native(error))
        return result, error

    def close(self):
        try:
            if self._cursor:
                self._cursor.close()
            if self._conn:
                self._conn.close()
        except:
            pass

