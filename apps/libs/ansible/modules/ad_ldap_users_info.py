#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: ad_ldap_users_info
short_description: List Active Directory users over LDAPS or StartTLS.
description:
    - Search the users under a search base with paged searches and return
      them in the format of the WinRM AD account gather method.
    - The connection is always encrypted; plain LDAP binds are never sent.
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
    domain_name:
        description: AD DNS domain name; used to derive the search base.
        type: str
    search_base:
        description: Search base DN; overrides the value derived from domain_name.
        type: str
    page_size:
        description: Entries per page; AD returns at most 1000 per page.
        type: int
        default: 500
'''

EXAMPLES = '''
- name: List AD users over LDAPS
  ad_ldap_users_info:
    login_host: dc01.example.com
    login_user: jms-pam@example.com
    login_password: secret
    domain_name: example.com
    search_base: OU=Staff,DC=example,DC=com
'''

RETURN = '''
user_details:
  description: Users with Name, SamAccountName, Enabled, LastLogonDate,
               PasswordLastSet, PasswordExpires and GlobalGroupMemberships.
  returned: success
  type: list
count:
  description: Number of users found.
  returned: success
  type: int
search_base:
  description: The search base that was used.
  returned: success
  type: str
'''

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

from libs.ansible.modules_utils.ad_ldap import (
    HAS_LDAP3,
    ADLdapClient,
    ADLdapError,
    connection_argument_spec,
    entry_user_detail,
)


def main():
    options = connection_argument_spec()
    options.update(
        domain_name=dict(type='str', required=False, default=''),
        search_base=dict(type='str', required=False, default=''),
        page_size=dict(type='int', required=False, default=500),
    )
    module = AnsibleModule(argument_spec=options, supports_check_mode=True)
    if not HAS_LDAP3:
        module.fail_json(msg=missing_required_lib('ldap3'))

    params = module.params
    try:
        client = ADLdapClient.from_params(params)
        search_base = client.resolve_search_base(params['domain_name'], params['search_base'])
        conn = client.bind(params['login_user'], params['login_password'])
        try:
            entries = client.search_users(conn, search_base, page_size=params['page_size'])
        finally:
            client.unbind(conn)
    except ADLdapError as error:
        module.fail_json(msg=str(error), reason_code=error.reason_code)

    users = [entry_user_detail(entry) for entry in entries]
    users = [user for user in users if user['SamAccountName']]
    module.exit_json(
        changed=False, user_details=users, count=len(users), search_base=search_base,
    )


if __name__ == '__main__':
    main()
