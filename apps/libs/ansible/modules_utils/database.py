"""Bounded database automation clients, independent of Django and Ansible.

Only server-provided connection options are accepted. Account SQL is generated
here, never by interpolating account names/passwords into a playbook template.
"""
import contextlib
import importlib
import os
import re
import ssl
import tempfile
from datetime import date, datetime
from decimal import Decimal


DATABASE_TYPES = ('dameng', 'oceanbase', 'clickhouse', 'db2', 'oracle')
ACCOUNT_DATABASE_TYPES = ('dameng', 'oceanbase', 'clickhouse')


class DatabaseAutomationError(ValueError):
    pass


def identifier(value):
    if not isinstance(value, str) or not value or len(value) > 128:
        raise DatabaseAutomationError('Invalid database account/schema name')
    if any(ord(char) < 32 for char in value):
        raise DatabaseAutomationError('Control characters are not allowed in database names')
    return '"' + value.replace('"', '""') + '"'


def json_value(value):
    if value is None or isinstance(value, (bool, int, float, str)):
        return value[:65536] if isinstance(value, str) else value
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value[:65536]).hex()
    # In particular, do not read an unbounded Oracle/DM LOB into the worker.
    return '<{} value omitted>'.format(type(value).__name__)


def safe_error(error, secrets=(), sensitive=False):
    if sensitive:
        # DDL error messages can echo the complete ALTER/CREATE USER statement.
        return 'Database account operation failed ({})'.format(type(error).__name__)
    message = str(error)
    for secret in secrets:
        if secret:
            for value in (secret, secret.replace("'", "''"), secret.replace('"', '""'),
                          secret.replace('\\', '\\\\').replace("'", "\\'")):
                message = message.replace(value, '********')
    return message[:2048]


class DatabaseClient:
    def __init__(self, database_type, host, port, user, password, database='',
                 options=None, connect_timeout=15):
        if database_type not in DATABASE_TYPES:
            raise DatabaseAutomationError('Unsupported database automation type')
        if isinstance(port, bool) or not 1 <= int(port) <= 65535:
            raise DatabaseAutomationError('Invalid database port')
        self.kind = database_type
        self.host, self.port = host, int(port)
        self.user, self.password, self.database = user, password, database or ''
        self.options = options or {}
        self.timeout = max(1, min(int(connect_timeout), 300))
        self.connection = None
        self.changed = False
        self.files = contextlib.ExitStack()
        self.tenant_mode = self.options.get('tenant_mode', 'mysql')
        if self.kind == 'oceanbase' and self.tenant_mode not in ('mysql', 'oracle'):
            raise DatabaseAutomationError('OceanBase tenant_mode must be mysql or oracle')

    @property
    def oracle_dialect(self):
        return self.kind in ('dameng', 'oracle') or (
            self.kind == 'oceanbase' and self.tenant_mode == 'oracle'
        )

    def certificate_file(self, name):
        value = self.options.get(name)
        if not value:
            return None
        directory = self.files.enter_context(tempfile.TemporaryDirectory(prefix='jms-database-tls-'))
        path = os.path.join(directory, name + '.pem')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(value)
        return path

    def connect(self):
        if self.connection is not None:
            return
        secure = bool(self.options.get('use_ssl'))
        # DPI uses a vendor-specific certificate store, not the asset PEM API.
        if secure and self.kind in ('dameng', 'oracle'):
            raise DatabaseAutomationError(
                'TLS for this database requires a vendor certificate store; '
                'plaintext fallback is not permitted'
            )
        if self.kind == 'dameng':
            driver = importlib.import_module('dmPython')
            self.connection = driver.connect(
                user=self.user, password=self.password, server=self.host,
                port=self.port, login_timeout=self.timeout * 1000,
            )
        elif self.kind == 'oceanbase':
            driver = importlib.import_module('pymysql')
            kwargs = dict(host=self.host, port=self.port, user=self.user,
                          password=self.password, connect_timeout=self.timeout,
                          read_timeout=self.timeout, write_timeout=self.timeout,
                          charset='utf8mb4', autocommit=False)
            if self.database and self.tenant_mode == 'mysql':
                kwargs['database'] = self.database
            if secure:
                context = ssl.create_default_context(cadata=self.options.get('ca_cert') or None)
                if self.options.get('allow_invalid_cert'):
                    context.check_hostname = False
                    context.verify_mode = ssl.CERT_NONE
                # PyMySQL verifies the TCP host. Do not weaken verification for a tunnel.
                if context.check_hostname and self.options.get('server_name', self.host) != self.host:
                    raise DatabaseAutomationError('Verified OceanBase TLS through a gateway is not supported')
                cert, key = self.certificate_file('client_cert'), self.certificate_file('client_key')
                if bool(cert) != bool(key):
                    raise DatabaseAutomationError('Both TLS client certificate and key are required')
                if cert:
                    context.load_cert_chain(cert, key)
                kwargs['ssl'] = context
            self.connection = driver.connect(**kwargs)
        elif self.kind == 'db2':
            if not self.database:
                raise DatabaseAutomationError('Db2 automation requires an explicit database name')
            for value in (self.host, self.database):
                if any(char in value for char in ';{}=\x00\r\n'):
                    raise DatabaseAutomationError('Invalid Db2 connection setting')
            driver = importlib.import_module('ibm_db_dbi')
            native = importlib.import_module('ibm_db')
            dsn = 'DATABASE={};HOSTNAME={};PORT={};PROTOCOL=TCPIP;'.format(
                self.database, self.host, self.port,
            )
            if secure:
                if self.options.get('allow_invalid_cert') or self.options.get('client_key'):
                    raise DatabaseAutomationError('Db2 TLS requires verified server authentication; PEM mTLS is unsupported')
                if self.options.get('server_name', self.host) != self.host:
                    raise DatabaseAutomationError('Verified Db2 TLS through a gateway is not supported')
                dsn += 'SECURITY=SSL;SSLClientHostnameValidation=Basic;'
                ca = self.certificate_file('ca_cert')
                if ca:
                    dsn += 'SSLServerCertificate={};'.format(ca)
            self.connection = driver.connect(
                dsn, self.user, self.password,
                conn_options={native.SQL_ATTR_LOGIN_TIMEOUT: self.timeout},
            )
        elif self.kind == 'clickhouse':
            driver = importlib.import_module('clickhouse_driver')
            kwargs = dict(host=self.host, port=self.port, user=self.user,
                          password=self.password, database=self.database or 'default',
                          connect_timeout=self.timeout, send_receive_timeout=self.timeout,
                          secure=secure, verify=not self.options.get('allow_invalid_cert', False))
            if secure:
                kwargs.update(server_hostname=self.options.get('server_name') or self.host,
                              ca_certs=self.certificate_file('ca_cert'),
                              certfile=self.certificate_file('client_cert'),
                              keyfile=self.certificate_file('client_key'))
                if bool(kwargs['certfile']) != bool(kwargs['keyfile']):
                    raise DatabaseAutomationError('Both TLS client certificate and key are required')
            self.connection = driver.Client(**kwargs)
        else:
            driver = importlib.import_module('oracledb')
            kwargs = dict(host=self.host, port=self.port, user=self.user,
                          password=self.password, service_name=self.database,
                          tcp_connect_timeout=self.timeout)
            if self.options.get('sysdba'):
                kwargs['mode'] = driver.SYSDBA
            self.connection = driver.connect(**kwargs)
            self.connection.call_timeout = self.timeout * 1000

    def close(self):
        try:
            if self.connection is not None:
                if self.kind == 'clickhouse':
                    self.connection.disconnect()
                else:
                    self.connection.close()
        finally:
            self.connection = None
            self.files.close()

    def rows(self, sql, params=None, limit=1000):
        self.connect()
        if self.kind == 'clickhouse':
            response = self.connection.execute(sql, params=params, with_column_types=True, settings={
                'max_result_rows': limit + 1, 'result_overflow_mode': 'break',
                'max_block_size': min(limit + 1, 1000),
            })
            # DDL returns [], INSERT can return a count; neither is a row set.
            if not isinstance(response, tuple) or len(response) != 2:
                return [], False
            rows, columns = response
            names = [column[0].lower() for column in columns]
            result = [dict(zip(names, map(json_value, row))) for row in rows[:limit]]
            return result, len(rows) > limit
        with contextlib.closing(self.connection.cursor()) as cursor:
            cursor.execute(sql, params) if params is not None else cursor.execute(sql)
            if not cursor.description:
                return [], False
            names = [column[0].lower() for column in cursor.description]
            rows = cursor.fetchmany(limit + 1)
            return [dict(zip(names, map(json_value, row))) for row in rows[:limit]], len(rows) > limit

    def execute(self, sql, params=None):
        self.rows(sql, params)
        if self.kind != 'clickhouse':
            self.connection.commit()

    def bind(self, *values):
        if self.kind == 'clickhouse':
            return ['%(p{})s'.format(i) for i in range(len(values))], {
                'p{}'.format(i): value for i, value in enumerate(values)
            }
        if self.kind == 'oceanbase':
            return ['%s'] * len(values), values
        if self.kind == 'oracle':
            return [':{}'.format(i + 1) for i in range(len(values))], values
        return ['?'] * len(values), values

    def ping(self):
        sql = 'SELECT 1 AS alive'
        if self.kind == 'db2':
            sql += ' FROM SYSIBM.SYSDUMMY1'
        elif self.oracle_dialect:
            sql += ' FROM DUAL'
        rows, _ = self.rows(sql, limit=1)
        if not rows:
            raise DatabaseAutomationError('Database returned no connectivity result')
        return {'is_available': True}

    def facts(self):
        if self.kind == 'db2':
            sql = 'SELECT SERVICE_LEVEL AS VERSION FROM SYSIBMADM.ENV_INST_INFO'
        elif self.oracle_dialect:
            sql = 'SELECT BANNER AS VERSION FROM V$VERSION'
        else:
            sql = 'SELECT VERSION() AS VERSION'
        rows, _ = self.rows(sql, limit=10)
        return {'version': '; '.join(str(row.get('version', '')) for row in rows)}

    def accounts(self):
        if self.kind == 'db2':
            # These are catalogued authorization IDs, not a directory enumeration.
            sql = "SELECT AUTHID AS USERNAME FROM SYSIBMADM.AUTHORIZATIONIDS WHERE AUTHIDTYPE = 'U'"
        elif self.kind == 'clickhouse':
            sql = 'SELECT name AS username, storage FROM system.users'
        elif self.oracle_dialect:
            sql = 'SELECT USERNAME, ACCOUNT_STATUS, DEFAULT_TABLESPACE FROM DBA_USERS'
        else:
            sql = 'SELECT USER AS username, HOST AS host FROM mysql.user'
        rows, truncated = self.rows(sql, limit=100000)
        if truncated:
            raise DatabaseAutomationError('Account collection limit exceeded; refusing a partial snapshot')
        result = {}
        tenant = self.user.partition('@')[2] if self.kind == 'oceanbase' else ''
        for row in rows:
            name = row.get('username')
            if not name:
                continue
            # Preserve the routable tenant identity in imported managed accounts.
            username = '{}@{}'.format(name, tenant) if tenant else name
            item = result.setdefault(username, dict(username=username, groups='',
                date_password_change=None, date_password_expired=None, date_last_login=None,
                detail={'source': 'database_catalog', 'records': []}))
            item['detail']['records'].append(row)
        return result

    def account_name(self, username):
        if self.kind == 'oceanbase':
            _, _, tenant = self.user.partition('@')
            name, separator, target_tenant = username.partition('@')
            if separator and target_tenant != tenant:
                raise DatabaseAutomationError('Cannot manage an account from another OceanBase tenant')
            username = name
        identifier(username)
        return username

    def account_exists(self, username, host='%'):
        if self.kind == 'clickhouse':
            marks, params = self.bind(username)
            rows, _ = self.rows('SELECT storage FROM system.users WHERE name = ' + marks[0], params)
            if rows and rows[0]['storage'] not in ('local_directory', 'replicated'):
                raise DatabaseAutomationError('This ClickHouse account is managed by XML/LDAP, not SQL access control')
            return bool(rows)
        if self.oracle_dialect:
            marks, params = self.bind(username)
            rows, _ = self.rows('SELECT USERNAME FROM DBA_USERS WHERE USERNAME = ' + marks[0], params)
        else:
            marks, params = self.bind(username, host)
            rows, _ = self.rows('SELECT USER FROM mysql.user WHERE USER = {} AND HOST = {}'.format(*marks), params)
        return bool(rows)

    def manage_account(self, action, username, password=None, host='%', check_mode=False):
        if self.kind not in ACCOUNT_DATABASE_TYPES:
            if self.kind == 'db2':
                raise DatabaseAutomationError('Db2 account creation/passwords/deletion belong to its OS/LDAP identity provider')
            raise DatabaseAutomationError('Account operations are not enabled for this database adapter')
        username = self.account_name(username)
        exists = self.account_exists(username, host)
        if action == 'remove_account':
            current = self.user.partition('@')[0] if self.kind == 'oceanbase' else self.user
            if username.casefold() == current.casefold() or username.upper() in ('SYSDBA', 'SYS', 'SYSSSO', 'SYSAUDITOR'):
                raise DatabaseAutomationError('Refusing to remove the execution account or a built-in system account')
            if not exists:
                return {'changed': False}
        elif action == 'change_secret' and not exists:
            raise DatabaseAutomationError('Account does not exist; password rotation never creates accounts')
        elif not isinstance(password, str) or not password or '\x00' in password:
            raise DatabaseAutomationError('A nonempty database password is required')
        if check_mode:
            return {'changed': True}
        verb = 'ALTER' if exists else 'CREATE'
        if self.oracle_dialect:
            if password is not None and ('"' in password or any(ord(c) < 32 for c in password)):
                raise DatabaseAutomationError('Oracle-family passwords cannot contain quotes or control characters')
            target = identifier(username)
            sql = 'DROP USER ' + target if action == 'remove_account' else '{} USER {} IDENTIFIED BY "{}"'.format(verb, target, password)
            self.execute(sql)
            self.changed = True
            if not exists:
                self.execute('GRANT CREATE SESSION TO ' + target)
        elif self.kind == 'clickhouse':
            # ClickHouse quoted identifiers also interpret backslash escapes.
            target = identifier(username.replace('\\', '\\\\'))
            marks, params = self.bind(password)
            sql = 'DROP USER ' + target if action == 'remove_account' else '{} USER {} IDENTIFIED WITH sha256_password BY {}'.format(verb, target, marks[0])
            self.execute(sql, None if action == 'remove_account' else params)
            self.changed = True
        else:
            marks, params = self.bind(username, host, password)
            target = '{}@{}'.format(marks[0], marks[1])
            if action == 'remove_account':
                self.execute('DROP USER ' + target, params[:2])
            else:
                self.execute('{} USER {} IDENTIFIED BY {}'.format(verb, target, marks[2]), params)
            self.changed = True
        return {'changed': True}

    def query(self, sql, max_rows=1000):
        if not isinstance(sql, str) or not sql.strip():
            raise DatabaseAutomationError('A nonempty SQL statement is required')
        import sqlparse

        statements = []
        for statement in sqlparse.split(sql):
            significant = sqlparse.format(statement, strip_comments=True).strip()
            if not significant:
                continue
            block = re.match(r'(?is)^(BEGIN|DECLARE)\b|^CREATE\s+(OR\s+REPLACE\s+)?((NON)?EDITIONABLE\s+)?(PROCEDURE|FUNCTION|TRIGGER|PACKAGE|TYPE)\b', significant)
            if self.oracle_dialect and not block:
                statement = statement.rstrip().removesuffix(';')
            statements.append(statement)
        if not statements:
            raise DatabaseAutomationError('A nonempty SQL statement is required')
        if self.kind == 'dameng' and self.database:
            self.rows('SET SCHEMA ' + identifier(self.database))
        if self.kind == 'oceanbase' and self.tenant_mode == 'oracle' and self.database:
            self.rows('ALTER SESSION SET CURRENT_SCHEMA = ' + identifier(self.database))
        results, truncated = [], False
        try:
            for statement in statements:
                rows, overflow = self.rows(statement, limit=max(1, min(int(max_rows), 10000)))
                results.append(rows)
                truncated = truncated or overflow
            if self.kind != 'clickhouse':
                self.connection.commit()
        except Exception:
            if self.connection is not None and self.kind != 'clickhouse':
                with contextlib.suppress(Exception):
                    self.connection.rollback()
            raise
        return {'query_result': results, 'rowcount': sum(map(len, results)),
                'truncated': truncated, 'changed': True}
