#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: ad_ldap_user
short_description: Change an Active Directory user password over LDAPS or StartTLS.
description:
    - Bind to a domain controller with the login account, locate the target
      user and write its unicodePwd attribute.
    - The connection is always encrypted; plain LDAP binds are never sent.
    - After the change, the new password is verified with a fresh bind to the
      same domain controller.
options:
    login_host:
        description: Domain controller address.
        type: str
        required: True
    login_port:
        description: Domain controller LDAP port.
        type: int
        default: 636
    login_user:
        description: Login account, preferably a UPN such as admin@example.com.
        type: str
        required: True
    login_password:
        description: Login account password.
        type: str
        required: True
    security:
        description: Use LDAPS (TLS from the start) or StartTLS.
        type: str
        choices: [ldaps, starttls]
        default: ldaps
    allow_invalid_cert:
        description: Skip server certificate validation.
        type: bool
        default: False
    tls_server_name:
        description: Certificate name to validate; defaults to login_host.
        type: str
    ca_cert:
        description: PEM encoded CA certificates; the system store is used when empty.
        type: str
    name:
        description: Target user (sAMAccountName, UPN or DOMAIN\\user).
        type: str
        required: True
    password:
        description: New password.
        type: str
        required: True
    old_password:
        description: Current password, required when mode is change.
        type: str
    mode:
        description:
            - reset sets the password with the login account's Reset Password permission.
            - change uses the target user's current password, like a user changing it.
        type: str
        choices: [reset, change]
        default: reset
    enforce_password_history:
        description:
            - Apply the domain password history policy to a reset.
            - Requires Windows Server 2012 or later.
        type: bool
        default: False
    unlock:
        description: Clear a lockout after a successful reset.
        type: bool
        default: False
    domain_name:
        description: AD DNS domain name; used to derive the search base.
        type: str
    search_base:
        description: Search base DN; overrides the value derived from domain_name.
        type: str
    verify:
        description: Bind as the target user with the new password after the change.
        type: bool
        default: True
    change_started_at:
        description:
            - Unix time when this change was first attempted (the change record creation).
            - Set only when retrying the record of an earlier attempt, so that a change
              that attempt applied is recognised. A new change never treats a refused
              rewrite as applied.
        type: int
        default: 0
'''

EXAMPLES = '''
- name: Reset an AD user password over LDAPS
  ad_ldap_user:
    login_host: dc01.example.com
    login_user: jms-pam@example.com
    login_password: secret
    domain_name: example.com
    name: alice
    password: NewPassword
'''

RETURN = '''
user_dn:
  description: The distinguished name of the changed user.
  returned: success
  type: str
auth_status:
  description: Result of verifying the new password with a fresh bind.
  returned: always
  type: str
  sample: accepted
reason_code:
  description: A stable classification for the result.
  returned: always
  type: str
change_succeeded:
  description: Whether AD accepted the password change.
  returned: always
  type: bool
'''

import time

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

from libs.ansible.modules_utils.ad_ldap import (
    ERROR_INVALID_PASSWORD,
    ERROR_PASSWORD_RESTRICTION,
    HAS_LDAP3,
    ADLdapClient,
    ADLdapError,
    connection_argument_spec,
)


def argument_spec():
    options = connection_argument_spec()
    options.update(
        name=dict(type='str', required=True),
        password=dict(type='str', required=True, no_log=True),
        old_password=dict(type='str', required=False, default='', no_log=True),
        mode=dict(
            type='str', required=False, default='reset',
            choices=['reset', 'change'],
        ),
        enforce_password_history=dict(type='bool', required=False, default=False),
        unlock=dict(type='bool', required=False, default=False),
        domain_name=dict(type='str', required=False, default=''),
        search_base=dict(type='str', required=False, default=''),
        verify=dict(type='bool', required=False, default=True),
        change_started_at=dict(type='int', required=False, default=0),
    )
    return options


# pwdLastSet and the change start time are compared on the domain controller's
# clock; the tolerance covers whole-second start times and the time to read it.
CLOCK_TOLERANCE_SECONDS = 5
# Used only if the domain controller does not report its time.
FALLBACK_CLOCK_SKEW_SECONDS = 300


def is_retry_of_applied_change(error, client, conn, user_dn, password, change_started_at):
    """A rejected retry can mean the new password is already set.

    If a previous run applied the change but lost its result, AD rejects the
    retry: password history refuses to reuse the new password, and change
    mode no longer accepts the old one. A successful bind alone does not prove
    it: during OldPasswordAllowedPeriod (60 minutes by default) AD still
    accepts a recently replaced password. Require that the password was also
    set after this change was first attempted.
    """
    if error.win32_code not in (ERROR_PASSWORD_RESTRICTION, ERROR_INVALID_PASSWORD):
        return False
    if not change_started_at:
        return False
    pwd_last_set = client.get_pwd_last_set(conn, user_dn)
    if pwd_last_set is None:
        return False
    server_time = client.get_server_time(conn)
    if server_time is None:
        earliest = change_started_at - FALLBACK_CLOCK_SKEW_SECONDS
    else:
        earliest = change_started_at + (server_time - time.time()) - CLOCK_TOLERANCE_SECONDS
    if pwd_last_set < earliest:
        return False
    auth_status, _, _ = client.check_password(user_dn, password)
    return auth_status == 'accepted'


def change_password(module, client):
    params = module.params
    old_password = params['old_password'] if params['mode'] == 'change' else ''
    if params['mode'] == 'change' and not old_password:
        raise ADLdapError(
            'The current managed password is required in change mode',
            'OLD_PASSWORD_REQUIRED',
        )

    conn = client.bind(params['login_user'], params['login_password'])
    try:
        user_dn = client.find_user(
            conn, params['name'], domain_name=params['domain_name'],
            search_base=params['search_base'],
        )
        if module.check_mode:
            return user_dn, False

        try:
            client.set_password(
                conn, user_dn, params['password'], old_password=old_password,
                enforce_history=params['enforce_password_history'],
            )
        except ADLdapError as error:
            if not is_retry_of_applied_change(
                error, client, conn, user_dn, params['password'],
                params['change_started_at'],
            ):
                raise
        if params['unlock'] and params['mode'] == 'reset':
            client.unlock(conn, user_dn)
    finally:
        client.unbind(conn)
    return user_dn, True


def main():
    module = AnsibleModule(argument_spec=argument_spec(), supports_check_mode=True)
    if not HAS_LDAP3:
        module.fail_json(msg=missing_required_lib('ldap3'))

    params = module.params
    # "unknown" is reserved for an inconclusive verification, which the
    # change secret manager records as unverified.
    result = {
        'changed': False,
        'auth_status': 'not_checked',
        'reason_code': '',
        'change_succeeded': False,
    }
    try:
        client = ADLdapClient.from_params(params)
        user_dn, changed = change_password(module, client)
    except ADLdapError as error:
        result.update(reason_code=error.reason_code, msg=str(error))
        module.fail_json(**result)

    result.update(user_dn=user_dn, changed=changed, change_succeeded=changed)
    if module.check_mode or not params['verify']:
        module.exit_json(**result)

    # Bind to the same domain controller so replication delay cannot hide
    # the change. Unknown results keep the change but mark it unverified.
    auth_status, reason_code, message = client.check_password(
        user_dn, params['password']
    )
    result.update(auth_status=auth_status, reason_code=reason_code)
    if auth_status == 'accepted':
        module.exit_json(**result)

    result['msg'] = 'Password changed, but verification failed: %s' % message
    if auth_status == 'rejected':
        module.fail_json(**result)
    # The change module succeeded authoritatively; let the manager keep the
    # new secret and record the verification as inconclusive.
    result['sync_candidate'] = True
    module.exit_json(**result)


if __name__ == '__main__':
    main()
