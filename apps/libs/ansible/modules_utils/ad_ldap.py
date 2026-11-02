import re
import ssl
from datetime import datetime, timezone

try:
    from ldap3 import BASE, NONE, SIMPLE, SUBTREE, Connection, Server, Tls
    from ldap3.core.exceptions import LDAPException, LDAPStartTLSError
    from ldap3.core.results import (
        RESULT_CONSTRAINT_VIOLATION,
        RESULT_INSUFFICIENT_ACCESS_RIGHTS,
        RESULT_INVALID_CREDENTIALS,
        RESULT_NO_SUCH_OBJECT,
        RESULT_SIZE_LIMIT_EXCEEDED,
        RESULT_SUCCESS,
        RESULT_UNAVAILABLE_CRITICAL_EXTENSION,
        RESULT_UNWILLING_TO_PERFORM,
    )
    from ldap3.utils.conv import escape_filter_chars
except ImportError:  # pragma: no cover - depends on the executor image
    HAS_LDAP3 = False
    Tls = object
else:
    HAS_LDAP3 = True

LDAPS = 'ldaps'
STARTTLS = 'starttls'
SECURITY_CHOICES = [LDAPS, STARTTLS]

# LDAP_SERVER_POLICY_HINTS_OID with BER SEQUENCE { INTEGER 1 } asks AD to
# apply password history to an administrative reset (Windows Server 2012+).
POLICY_HINTS_OID = '1.2.840.113556.1.4.2239'
POLICY_HINTS_VALUE = b'\x30\x03\x02\x01\x01'

# Win32 codes at the start of AD diagnostic messages, e.g. "0000052D: ...".
ERROR_ACCESS_DENIED = 0x5
ERROR_GEN_FAILURE = 0x1F
ERROR_INVALID_PASSWORD = 0x56
ERROR_PASSWORD_RESTRICTION = 0x52D

# Sub-codes in AD bind failures, e.g. "AcceptSecurityContext error, data 52e".
# Apart from 525/52e/775, AD only reports them when the password is correct.
BIND_SUBCODES = {
    '525': ('rejected', 'USER_NOT_FOUND'),
    '52e': ('rejected', 'AUTHENTICATION_FAILED'),
    '530': ('unknown', 'LOGON_TIME_RESTRICTED'),
    '531': ('unknown', 'WORKSTATION_RESTRICTED'),
    '532': ('unknown', 'PASSWORD_EXPIRED'),
    '533': ('unknown', 'ACCOUNT_DISABLED'),
    '701': ('unknown', 'ACCOUNT_EXPIRED'),
    '773': ('unknown', 'PASSWORD_MUST_CHANGE'),
    '775': ('unknown', 'ACCOUNT_LOCKED'),
}

USER_ATTRIBUTES = ['sAMAccountName', 'userPrincipalName']

# Seconds between 1601-01-01 (Windows FILETIME epoch) and 1970-01-01.
FILETIME_EPOCH_OFFSET = 11644473600


def connection_argument_spec():
    return dict(
        login_host=dict(type='str', required=True),
        login_port=dict(type='int', required=False, default=636),
        login_user=dict(type='str', required=True),
        login_password=dict(type='str', required=True, no_log=True),
        security=dict(
            type='str', required=False, default=LDAPS,
            choices=SECURITY_CHOICES,
        ),
        allow_invalid_cert=dict(type='bool', required=False, default=False),
        tls_server_name=dict(type='str', required=False, default=''),
        ca_cert=dict(type='str', required=False, default=''),
        connect_timeout=dict(type='int', required=False, default=15),
    )


class ADLdapError(Exception):
    def __init__(self, message, reason_code='LDAP_ERROR',
                 auth_status='unknown', win32_code=None):
        super().__init__(message)
        self.reason_code = reason_code
        self.auth_status = auth_status
        self.win32_code = win32_code


class StrictTls(Tls):
    """TLS settings that validate certificates with the standard library.

    ldap3 matches certificate names itself, ignores IP SANs on Python 3.12+
    and accepts any certificate when a valid name is "*".
    """

    def __init__(self, server_name, ca_cert='', allow_invalid_cert=False):
        validate = ssl.CERT_NONE if allow_invalid_cert else ssl.CERT_REQUIRED
        super().__init__(validate=validate, sni=server_name)
        self.server_name = server_name
        self.ca_cert = ca_cert or None
        self.allow_invalid_cert = allow_invalid_cert

    def create_context(self):
        context = ssl.create_default_context(cadata=self.ca_cert)
        # Python 3.13 enables strict RFC 5280 checks by default; many internal
        # enterprise CAs omit fields such as the Authority Key Identifier.
        # Chain, expiry and host name are still validated.
        context.verify_flags &= ~getattr(ssl, 'VERIFY_X509_STRICT', 0)
        if self.allow_invalid_cert:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        return context

    def wrap_socket(self, connection, do_handshake=False):
        context = self.create_context()
        connection.socket = context.wrap_socket(
            connection.socket,
            server_side=False,
            do_handshake_on_connect=do_handshake,
            server_hostname=self.server_name,
        )


def domain_to_base_dn(domain_name):
    domain_name = (domain_name or '').strip().strip('.')
    if not domain_name:
        return ''
    labels = domain_name.split('.')
    for label in labels:
        if not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?', label):
            raise ADLdapError(
                'Invalid domain name: %s' % domain_name, 'INVALID_DOMAIN_NAME'
            )
    return ','.join('DC=%s' % label for label in labels)


def build_user_filter(username):
    username = (username or '').strip()
    if not username:
        raise ADLdapError('Username is required', 'USERNAME_REQUIRED')

    if '\\' in username:
        username = username.split('\\', 1)[1]
    if '@' in username:
        local = username.split('@', 1)[0]
        identity = '(|(userPrincipalName=%s)(sAMAccountName=%s))' % (
            escape_filter_chars(username), escape_filter_chars(local)
        )
    else:
        identity = '(sAMAccountName=%s)' % escape_filter_chars(username)
    return '(&(objectCategory=person)(objectClass=user)%s)' % identity


def get_win32_code(message):
    matched = re.match(r'\s*([0-9A-Fa-f]{8})\s*:', message or '')
    if not matched:
        return None
    return int(matched.group(1), 16)


def classify_bind_result(result):
    message = result.get('message') or ''
    description = result.get('description') or 'bind failed'
    matched = re.search(r'\bdata ([0-9a-fA-F]{3,4})\b', message)
    if matched:
        subcode = matched.group(1).lower()
        if subcode in BIND_SUBCODES:
            auth_status, reason_code = BIND_SUBCODES[subcode]
            return ADLdapError(
                'LDAP bind failed: %s (%s)' % (reason_code, message),
                reason_code, auth_status,
            )
    if result.get('result') == RESULT_INVALID_CREDENTIALS:
        return ADLdapError(
            'LDAP bind failed: %s' % (message or description),
            'AUTHENTICATION_FAILED', 'rejected',
        )
    return ADLdapError(
        'LDAP bind failed: %s %s' % (description, message),
        'BIND_FAILED',
    )


def classify_modify_result(result):
    code = result.get('result')
    message = result.get('message') or ''
    description = result.get('description') or ''
    win32_code = get_win32_code(message)

    if win32_code == ERROR_PASSWORD_RESTRICTION:
        reason_code = 'PASSWORD_POLICY_VIOLATION'
        hint = ('the new password does not meet the domain password policy '
                '(length, complexity, history or minimum password age)')
    elif win32_code == ERROR_INVALID_PASSWORD:
        reason_code = 'OLD_PASSWORD_INCORRECT'
        hint = 'the current managed password was not accepted by AD'
    elif code == RESULT_INSUFFICIENT_ACCESS_RIGHTS or win32_code == ERROR_ACCESS_DENIED:
        reason_code = 'INSUFFICIENT_ACCESS_RIGHTS'
        hint = ('the login account lacks the Reset Password or Change '
                'Password permission on the target user')
    elif code == RESULT_UNAVAILABLE_CRITICAL_EXTENSION:
        reason_code = 'POLICY_HINTS_UNSUPPORTED'
        hint = ('the domain controller does not support enforcing password '
                'history on reset (requires Windows Server 2012 or later)')
    elif code == RESULT_UNWILLING_TO_PERFORM:
        reason_code = 'UNWILLING_TO_PERFORM'
        hint = ('the domain controller refused the change; password changes '
                'require an encrypted connection and a password policy match')
    elif code == RESULT_CONSTRAINT_VIOLATION:
        reason_code = 'CONSTRAINT_VIOLATION'
        hint = 'the domain controller rejected the new password'
    elif code == RESULT_NO_SUCH_OBJECT:
        reason_code = 'USER_NOT_FOUND'
        hint = 'the target user no longer exists'
    else:
        reason_code = 'MODIFY_FAILED'
        hint = description or 'unknown error'
    return ADLdapError(
        'Change password failed: %s (%s %s)' % (hint, description, message),
        reason_code, win32_code=win32_code,
    )


def classify_connection_error(error, conn=None):
    # ldap3 wraps the original error repeatedly; last_error keeps it readable.
    message = getattr(conn, 'last_error', None) or str(error)
    lowered = message.lower()
    if isinstance(error, LDAPStartTLSError):
        reason_code = 'STARTTLS_FAILED'
    elif 'certificate verify failed' in lowered or 'hostname mismatch' in lowered:
        reason_code = 'TLS_CERTIFICATE_INVALID'
    elif 'ssl' in lowered or 'tls' in lowered:
        reason_code = 'TLS_HANDSHAKE_FAILED'
    elif 'timed out' in lowered or 'timeout' in lowered:
        reason_code = 'LDAP_TIMEOUT'
    else:
        reason_code = 'CONNECTION_FAILED'
    return ADLdapError('LDAP connection failed: %s' % message, reason_code)


class ADLdapClient:
    def __init__(self, host, port, security=LDAPS, tls_server_name='',
                 ca_cert='', allow_invalid_cert=False, connect_timeout=15):
        if security not in SECURITY_CHOICES:
            raise ADLdapError(
                'Unsupported LDAP security mode: %s' % security,
                'INVALID_SECURITY_MODE',
            )
        self.host = host
        # Later binds reuse the domain controller of the first connection so
        # verification is not affected by replication between DCs.
        self.pinned_address = None
        self.port = int(port)
        self.security = security
        self.timeout = max(int(connect_timeout or 15), 1)
        self.tls = StrictTls(
            (tls_server_name or '').strip() or host,
            ca_cert=(ca_cert or '').strip(),
            allow_invalid_cert=allow_invalid_cert,
        )

    @classmethod
    def from_params(cls, params):
        return cls(
            params['login_host'], params['login_port'],
            security=params['security'],
            tls_server_name=params['tls_server_name'],
            ca_cert=params['ca_cert'],
            allow_invalid_cert=params['allow_invalid_cert'],
            connect_timeout=params['connect_timeout'],
        )

    def bind(self, user, password):
        """Open an encrypted connection and bind; never binds in plaintext."""
        if not password:
            raise ADLdapError(
                'Password is required for LDAP bind', 'PASSWORD_REQUIRED',
                'rejected',
            )
        server = Server(
            self.pinned_address or self.host, port=self.port,
            use_ssl=self.security == LDAPS, tls=self.tls, get_info=NONE,
            connect_timeout=self.timeout,
        )
        conn = Connection(
            server, user=user, password=password, authentication=SIMPLE,
            raise_exceptions=False, receive_timeout=self.timeout,
            auto_referrals=False,
        )
        try:
            conn.open()
            self.pin_address(conn)
            if self.security == STARTTLS:
                conn.start_tls()
            if not (conn.server.ssl or conn.tls_started):
                raise ADLdapError(
                    'LDAP connection is not encrypted', 'TLS_NOT_ESTABLISHED'
                )
            bound = conn.bind()
        except ADLdapError:
            self.unbind(conn)
            raise
        except (LDAPException, OSError, ssl.SSLError) as error:
            self.unbind(conn)
            raise classify_connection_error(error, conn)

        if not bound:
            result = dict(conn.result or {})
            self.unbind(conn)
            raise classify_bind_result(result)
        return conn

    def pin_address(self, conn):
        if self.pinned_address:
            return
        try:
            address = conn.socket.getpeername()[0]
        except (AttributeError, OSError, IndexError):
            return
        if ':' not in address:
            self.pinned_address = address

    @staticmethod
    def unbind(conn):
        try:
            conn.unbind()
        except Exception:
            pass

    def find_user(self, conn, username, domain_name='', search_base=''):
        search_base = (search_base or '').strip() or domain_to_base_dn(domain_name)
        if not search_base:
            raise ADLdapError(
                'Search base is required when the directory service has no '
                'domain name', 'SEARCH_BASE_REQUIRED',
            )
        search_filter = build_user_filter(username)
        try:
            conn.search(
                search_base, search_filter, search_scope=SUBTREE,
                attributes=USER_ATTRIBUTES, size_limit=2,
            )
        except (LDAPException, OSError) as error:
            raise classify_connection_error(error, conn)

        result = conn.result or {}
        entries = [
            entry for entry in (conn.response or [])
            if entry.get('type') == 'searchResEntry'
        ]
        if result.get('result') == RESULT_SIZE_LIMIT_EXCEEDED or len(entries) > 1:
            raise ADLdapError(
                'More than one AD user matches %s under %s' % (
                    username, search_base
                ), 'USER_AMBIGUOUS',
            )
        if not entries:
            if result.get('result') not in (RESULT_SUCCESS, RESULT_NO_SUCH_OBJECT):
                raise ADLdapError(
                    'Search AD user failed: %s %s' % (
                        result.get('description'), result.get('message')
                    ), 'SEARCH_FAILED',
                )
            raise ADLdapError(
                'AD user not found: %s under %s' % (username, search_base),
                'USER_NOT_FOUND',
            )
        return entries[0]['dn']

    @staticmethod
    def set_password(conn, user_dn, new_password, old_password=None,
                     enforce_history=False):
        controls = None
        if enforce_history and not old_password:
            controls = [(POLICY_HINTS_OID, True, POLICY_HINTS_VALUE)]
        try:
            changed = conn.extend.microsoft.modify_password(
                user_dn, new_password, old_password=old_password or None,
                controls=controls,
            )
        except (LDAPException, OSError) as error:
            raise classify_connection_error(error, conn)
        if not changed:
            raise classify_modify_result(dict(conn.result or {}))

    @staticmethod
    def unlock(conn, user_dn):
        try:
            unlocked = conn.extend.microsoft.unlock_account(user_dn)
        except (LDAPException, OSError) as error:
            raise classify_connection_error(error, conn)
        if unlocked is not True:
            result = dict(conn.result or {})
            raise ADLdapError(
                'Unlock account failed: %s %s' % (
                    result.get('description'), result.get('message')
                ), 'UNLOCK_FAILED',
            )

    @staticmethod
    def get_pwd_last_set(conn, user_dn):
        """Return the user's pwdLastSet as a Unix timestamp, or None."""
        try:
            conn.search(user_dn, '(objectClass=*)', search_scope=BASE,
                        attributes=['pwdLastSet'])
        except (LDAPException, OSError) as error:
            raise classify_connection_error(error, conn)
        for entry in conn.response or []:
            if entry.get('type') != 'searchResEntry':
                continue
            value = (entry.get('attributes') or {}).get('pwdLastSet')
            if isinstance(value, (list, tuple)):
                value = value[0] if value else None
            if hasattr(value, 'timestamp'):
                return value.timestamp()
            try:
                filetime = int(value)
            except (TypeError, ValueError):
                return None
            return filetime / 10 ** 7 - FILETIME_EPOCH_OFFSET if filetime > 0 else None
        return None

    @staticmethod
    def get_server_time(conn):
        """Return the domain controller's clock (rootDSE currentTime) as a Unix timestamp."""
        try:
            conn.search('', '(objectClass=*)', search_scope=BASE, attributes=['currentTime'])
        except (LDAPException, OSError):
            return None
        for entry in conn.response or []:
            value = (entry.get('attributes') or {}).get('currentTime')
            if isinstance(value, (list, tuple)):
                value = value[0] if value else None
            if hasattr(value, 'timestamp'):
                return value.timestamp()
            matched = re.match(r'(\d{14})', str(value or ''))
            if matched:
                parsed = datetime.strptime(matched.group(1), '%Y%m%d%H%M%S')
                return parsed.replace(tzinfo=timezone.utc).timestamp()
        return None

    def check_password(self, user, password):
        """Bind as the user. Returns (auth_status, reason_code, message)."""
        try:
            conn = self.bind(user, password)
        except ADLdapError as error:
            return error.auth_status, error.reason_code, str(error)
        self.unbind(conn)
        return 'accepted', 'AUTHENTICATION_ACCEPTED', ''
