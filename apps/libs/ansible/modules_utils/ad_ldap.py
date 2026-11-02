import re
import ssl
from datetime import datetime, timezone

try:
    from ldap3 import (
        BASE, MODIFY_ADD, MODIFY_REPLACE, NONE, SIMPLE, SUBTREE, Connection, Server, Tls,
    )
    from ldap3.core.exceptions import LDAPException, LDAPStartTLSError
    from ldap3.core.results import (
        RESULT_ATTRIBUTE_OR_VALUE_EXISTS,
        RESULT_CONSTRAINT_VIOLATION,
        RESULT_ENTRY_ALREADY_EXISTS,
        RESULT_INSUFFICIENT_ACCESS_RIGHTS,
        RESULT_INVALID_CREDENTIALS,
        RESULT_NO_SUCH_OBJECT,
        RESULT_NOT_ALLOWED_ON_NON_LEAF,
        RESULT_SIZE_LIMIT_EXCEEDED,
        RESULT_SUCCESS,
        RESULT_UNAVAILABLE_CRITICAL_EXTENSION,
        RESULT_UNWILLING_TO_PERFORM,
    )
    from ldap3.utils.conv import escape_filter_chars
    from ldap3.utils.dn import escape_rdn, parse_dn
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
ERROR_USER_EXISTS = 0x524
ERROR_DS_NAME_NOT_UNIQUE = 0x21C8

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
PROTECTION_ATTRIBUTES = ['userAccountControl', 'adminCount', 'isCriticalSystemObject']
GATHER_ATTRIBUTES = [
    'name', 'sAMAccountName', 'userAccountControl', 'lastLogonTimestamp',
    'pwdLastSet', 'msDS-UserPasswordExpiryTimeComputed', 'memberOf',
]
USER_OBJECT_FILTER = '(&(objectCategory=person)(objectClass=user))'
PAGED_RESULTS_OID = '1.2.840.113556.1.4.319'

# Seconds between 1601-01-01 (Windows FILETIME epoch) and 1970-01-01.
FILETIME_EPOCH_OFFSET = 11644473600
# FILETIME used by AD for "never", e.g. a password that does not expire.
FILETIME_NEVER = 0x7FFFFFFFFFFFFFFF

UF_ACCOUNTDISABLE = 0x2
UF_NORMAL_ACCOUNT = 0x200

SAM_ACCOUNT_NAME_MAX_LENGTH = 20
SAM_ACCOUNT_NAME_INVALID_CHARS = set('"/\\[]:;|=,+*?<>@')


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


def split_names(value):
    return [item.strip() for item in (value or '').split(',') if item.strip()]


def user_identity(username, domain_name=''):
    """Return (sAMAccountName, userPrincipalName) for an account username."""
    username = (username or '').strip()
    if '\\' in username:
        username = username.split('\\', 1)[1]
    if '@' in username:
        return username.split('@', 1)[0], username
    domain_name = (domain_name or '').strip().strip('.')
    return username, ('%s@%s' % (username, domain_name) if domain_name else None)


def validate_sam_account_name(sam):
    if not sam:
        raise ADLdapError('Username is required', 'USERNAME_REQUIRED')
    if len(sam) > SAM_ACCOUNT_NAME_MAX_LENGTH:
        raise ADLdapError(
            'AD logon names (sAMAccountName) are limited to %d characters: %s' % (
                SAM_ACCOUNT_NAME_MAX_LENGTH, sam
            ), 'INVALID_ACCOUNT_NAME',
        )
    invalid = sorted(set(sam) & SAM_ACCOUNT_NAME_INVALID_CHARS)
    if invalid or sam.endswith('.') or any(ord(ch) < 32 for ch in sam):
        raise ADLdapError(
            'AD logon name contains characters that are not allowed: %s' % sam,
            'INVALID_ACCOUNT_NAME',
        )


def first_value(attributes, name):
    value = (attributes or {}).get(name)
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def filetime_to_datetime(value):
    """Convert an AD FILETIME (100 ns since 1601) to an aware UTC datetime."""
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        filetime = int(value)
    except (TypeError, ValueError):
        return None
    if filetime <= 0 or filetime >= FILETIME_NEVER:
        return None
    return datetime.fromtimestamp(filetime / 10 ** 7 - FILETIME_EPOCH_OFFSET, timezone.utc)


def unescape_dn_value(value):
    """Undo RFC 4514 escaping in an attribute value taken from a DN."""
    data = bytearray()
    index = 0
    while index < len(value):
        char = value[index]
        if char == '\\' and index + 1 < len(value):
            pair = value[index + 1:index + 3]
            if len(pair) == 2 and re.fullmatch(r'[0-9A-Fa-f]{2}', pair):
                data.append(int(pair, 16))
                index += 3
                continue
            data.extend(value[index + 1].encode('utf-8'))
            index += 2
            continue
        data.extend(char.encode('utf-8'))
        index += 1
    return data.decode('utf-8', 'replace')


def rdn_value(dn):
    """Return the value of the first RDN, e.g. the group name of a group DN."""
    try:
        return unescape_dn_value(parse_dn(dn)[0][1])
    except Exception:
        return dn


def is_protected_entry(attributes):
    admin_count = first_value(attributes, 'adminCount')
    critical = first_value(attributes, 'isCriticalSystemObject')
    return str(admin_count or '').strip() == '1' or str(critical or '').upper() == 'TRUE'


def entry_user_detail(entry):
    """Map an LDAP user entry to the record of the WinRM AD gather method."""
    attributes = entry.get('attributes') or {}

    def iso(name):
        value = filetime_to_datetime(first_value(attributes, name))
        return value.isoformat() if value else None

    try:
        uac = int(first_value(attributes, 'userAccountControl') or 0)
    except (TypeError, ValueError):
        uac = 0
    member_of = attributes.get('memberOf') or []
    if isinstance(member_of, str):
        member_of = [member_of]
    return {
        'Name': first_value(attributes, 'name'),
        'SamAccountName': first_value(attributes, 'sAMAccountName'),
        'Enabled': not uac & UF_ACCOUNTDISABLE,
        'LastLogonDate': iso('lastLogonTimestamp'),
        'PasswordLastSet': iso('pwdLastSet'),
        'PasswordExpires': iso('msDS-UserPasswordExpiryTimeComputed'),
        'GlobalGroupMemberships': [rdn_value(dn) for dn in member_of],
    }


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


def classify_operation_result(result, action, access_hint):
    """Classify a failed add, delete or modify of an account or group."""
    code = result.get('result')
    message = result.get('message') or ''
    description = result.get('description') or ''
    win32_code = get_win32_code(message)
    if win32_code == ERROR_PASSWORD_RESTRICTION:
        reason_code = 'PASSWORD_POLICY_VIOLATION'
        hint = ('the password does not meet the domain password policy '
                '(length, complexity or history)')
    elif code == RESULT_INSUFFICIENT_ACCESS_RIGHTS or win32_code == ERROR_ACCESS_DENIED:
        reason_code = 'INSUFFICIENT_ACCESS_RIGHTS'
        hint = access_hint
    elif code == RESULT_ENTRY_ALREADY_EXISTS or win32_code in (
            ERROR_USER_EXISTS, ERROR_DS_NAME_NOT_UNIQUE):
        reason_code = 'ACCOUNT_EXISTS'
        hint = ('an object with this name or logon name already exists, '
                'possibly outside the search scope')
    elif code == RESULT_NOT_ALLOWED_ON_NON_LEAF:
        reason_code = 'NOT_LEAF'
        hint = 'the account has child objects and cannot be deleted'
    elif code == RESULT_NO_SUCH_OBJECT:
        reason_code = 'OBJECT_NOT_FOUND'
        hint = 'the target organizational unit or object does not exist'
    elif code == RESULT_UNWILLING_TO_PERFORM:
        reason_code = 'UNWILLING_TO_PERFORM'
        hint = 'the domain controller refused the operation'
    elif code == RESULT_CONSTRAINT_VIOLATION:
        reason_code = 'CONSTRAINT_VIOLATION'
        hint = 'the domain controller rejected a value'
    else:
        reason_code = 'OPERATION_FAILED'
        hint = description or 'unknown error'
    return ADLdapError(
        '%s failed: %s (%s %s)' % (action, hint, description, message),
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

    @staticmethod
    def resolve_search_base(domain_name='', search_base=''):
        search_base = (search_base or '').strip() or domain_to_base_dn(domain_name)
        if not search_base:
            raise ADLdapError(
                'Search base is required when the directory service has no '
                'domain name', 'SEARCH_BASE_REQUIRED',
            )
        return search_base

    def find_user(self, conn, username, domain_name='', search_base=''):
        return self.find_user_entry(conn, username, domain_name, search_base)['dn']

    def find_user_entry(self, conn, username, domain_name='', search_base='',
                        attributes=None):
        search_base = self.resolve_search_base(domain_name, search_base)
        search_filter = build_user_filter(username)
        try:
            conn.search(
                search_base, search_filter, search_scope=SUBTREE,
                attributes=USER_ATTRIBUTES + list(attributes or []), size_limit=2,
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
        return entries[0]

    @staticmethod
    def find_group(conn, name, search_base):
        search_filter = '(&(objectClass=group)(|(sAMAccountName=%s)(cn=%s)))' % (
            escape_filter_chars(name), escape_filter_chars(name)
        )
        try:
            conn.search(search_base, search_filter, search_scope=SUBTREE,
                        attributes=['sAMAccountName'], size_limit=2)
        except (LDAPException, OSError) as error:
            raise classify_connection_error(error, conn)
        result = conn.result or {}
        entries = [e for e in (conn.response or []) if e.get('type') == 'searchResEntry']
        if result.get('result') == RESULT_SIZE_LIMIT_EXCEEDED or len(entries) > 1:
            raise ADLdapError('More than one AD group matches %s' % name, 'GROUP_AMBIGUOUS')
        if not entries:
            raise ADLdapError(
                'AD group not found: %s under %s' % (name, search_base), 'GROUP_NOT_FOUND'
            )
        return entries[0]['dn']

    @staticmethod
    def create_user(conn, container_dn, sam, upn, password):
        """Create an enabled user with its password in a single add.

        AD only accepts the add when the password meets the policy, so a
        rejected password never leaves a half-created account behind.
        """
        validate_sam_account_name(sam)
        user_dn = 'CN=%s,%s' % (escape_rdn(sam), container_dn)
        attributes = {
            'objectClass': ['top', 'person', 'organizationalPerson', 'user'],
            'sAMAccountName': sam,
            'unicodePwd': ('"%s"' % password).encode('utf-16-le'),
            'userAccountControl': str(UF_NORMAL_ACCOUNT),
        }
        if upn:
            attributes['userPrincipalName'] = upn
        try:
            created = conn.add(user_dn, attributes=attributes)
        except (LDAPException, OSError) as error:
            raise classify_connection_error(error, conn)
        if not created:
            raise classify_operation_result(
                dict(conn.result or {}), 'Create account',
                'the login account lacks the Create User Objects permission '
                'on the target organizational unit',
            )
        return user_dn

    @staticmethod
    def add_to_groups(conn, user_dn, group_dns):
        """Add the user to groups; existing memberships are kept as is."""
        added = []
        for group_dn in group_dns:
            try:
                ok = conn.modify(group_dn, {'member': [(MODIFY_ADD, [user_dn])]})
            except (LDAPException, OSError) as error:
                raise classify_connection_error(error, conn)
            result = dict(conn.result or {})
            if ok:
                added.append(group_dn)
            elif result.get('result') not in (
                    RESULT_ENTRY_ALREADY_EXISTS, RESULT_ATTRIBUTE_OR_VALUE_EXISTS):
                raise classify_operation_result(
                    result, 'Add account to group %s' % rdn_value(group_dn),
                    'the login account lacks write permission on the group members',
                )
        return added

    @staticmethod
    def disable_user(conn, user_dn, user_account_control):
        """Disable the account. Returns False when it was already disabled."""
        try:
            uac = int(user_account_control or UF_NORMAL_ACCOUNT)
        except (TypeError, ValueError):
            uac = UF_NORMAL_ACCOUNT
        if uac & UF_ACCOUNTDISABLE:
            return False
        try:
            ok = conn.modify(user_dn, {
                'userAccountControl': [(MODIFY_REPLACE, [str(uac | UF_ACCOUNTDISABLE)])]
            })
        except (LDAPException, OSError) as error:
            raise classify_connection_error(error, conn)
        if not ok:
            raise classify_operation_result(
                dict(conn.result or {}), 'Disable account',
                'the login account lacks write permission on userAccountControl',
            )
        return True

    @staticmethod
    def delete_user(conn, user_dn):
        try:
            ok = conn.delete(user_dn)
        except (LDAPException, OSError) as error:
            raise classify_connection_error(error, conn)
        if not ok:
            raise classify_operation_result(
                dict(conn.result or {}), 'Delete account',
                'the login account lacks the Delete User Objects permission',
            )

    @staticmethod
    def get_login_sam(conn):
        """Return the sAMAccountName of the bound account, from Who Am I."""
        try:
            identity = conn.extend.standard.who_am_i()
        except Exception:
            return None
        identity = str(identity or '')
        if identity.startswith('u:'):
            identity = identity[2:]
        if '\\' in identity:
            return identity.split('\\', 1)[1]
        return identity.split('@', 1)[0] or None

    @staticmethod
    def search_users(conn, search_base, page_size=500, attributes=None):
        """Return all user entries under search_base using paged searches."""
        entries = []
        cookie = None
        while True:
            try:
                conn.search(
                    search_base, USER_OBJECT_FILTER, search_scope=SUBTREE,
                    attributes=attributes or GATHER_ATTRIBUTES,
                    paged_size=max(int(page_size or 500), 1), paged_cookie=cookie,
                )
            except (LDAPException, OSError) as error:
                raise classify_connection_error(error, conn)
            result = conn.result or {}
            if result.get('result') != RESULT_SUCCESS:
                raise ADLdapError(
                    'Search AD users failed: %s %s' % (
                        result.get('description'), result.get('message')
                    ), 'SEARCH_FAILED',
                )
            entries.extend(
                e for e in (conn.response or []) if e.get('type') == 'searchResEntry'
            )
            control = (result.get('controls') or {}).get(PAGED_RESULTS_OID) or {}
            cookie = (control.get('value') or {}).get('cookie')
            if not cookie:
                return entries

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
