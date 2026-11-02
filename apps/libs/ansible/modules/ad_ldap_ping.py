#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: ad_ldap_ping
short_description: Verify an Active Directory credential with an encrypted LDAP bind.
description:
    - Open an LDAPS or StartTLS connection to a domain controller and bind
      with the supplied credential. Plain LDAP binds are never sent.
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
        description: Account to bind, preferably a UPN such as alice@example.com.
        type: str
        required: True
    login_password:
        description: Account password.
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
    fail_on_unknown:
        description:
            - Fail when the result is inconclusive, for example a network or
              TLS error, or an account that is disabled, locked or expired.
        type: bool
        default: True
'''

EXAMPLES = '''
- name: Verify an AD account over LDAPS
  ad_ldap_ping:
    login_host: dc01.example.com
    login_user: alice@example.com
    login_password: secret
'''

RETURN = '''
is_available:
  description: Whether the bind succeeded.
  returned: always
  type: bool
auth_status:
  description: Whether the credential was accepted, rejected, or could not be verified.
  returned: always
  type: str
  sample: accepted
reason_code:
  description: A stable classification for the result.
  returned: always
  type: str
  sample: AUTHENTICATION_ACCEPTED
'''

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

from libs.ansible.modules_utils.ad_ldap import (
    HAS_LDAP3,
    ADLdapClient,
    ADLdapError,
    connection_argument_spec,
)


def main():
    options = connection_argument_spec()
    options['fail_on_unknown'] = dict(type='bool', required=False, default=True)
    module = AnsibleModule(argument_spec=options, supports_check_mode=True)
    if not HAS_LDAP3:
        module.fail_json(msg=missing_required_lib('ldap3'))

    params = module.params
    try:
        client = ADLdapClient.from_params(params)
    except ADLdapError as error:
        module.fail_json(
            msg=str(error), is_available=False,
            auth_status='unknown', reason_code=error.reason_code,
        )

    auth_status, reason_code, message = client.check_password(
        params['login_user'], params['login_password']
    )
    result = {
        'changed': False,
        'is_available': auth_status == 'accepted',
        'auth_status': auth_status,
        'reason_code': reason_code,
    }
    if auth_status == 'accepted':
        module.exit_json(**result)

    result['msg'] = message
    if auth_status == 'rejected' or params['fail_on_unknown']:
        module.fail_json(**result)
    module.exit_json(**result)


if __name__ == '__main__':
    main()
