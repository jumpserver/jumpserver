#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: ad_ldap_account
short_description: Create, update or remove an Active Directory user over LDAPS or StartTLS.
description:
    - With state present, create the user in an organizational unit, or reset
      the password of an existing user, and optionally add it to groups.
    - With state absent, delete or disable the user. Protected accounts
      (adminCount=1 or critical system objects) and the login account itself
      are never removed.
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
    name:
        description: Target user (sAMAccountName, UPN or DOMAIN\\user).
        type: str
        required: True
    password:
        description: Password to set, required when state is present.
        type: str
    state:
        description: present creates or updates the user, absent removes it.
        type: str
        choices: [present, absent]
        default: present
    ou:
        description:
            - Organizational unit DN where new users are created; existing users
              are looked up only under it.
            - When empty, existing users are looked up in the whole domain and
              new users are created in CN=Users.
        type: str
    groups:
        description: Comma separated group names to add the user to (present only).
        type: str
    disable_only:
        description: Disable the user instead of deleting it (absent only).
        type: bool
        default: False
    domain_name:
        description: AD DNS domain name; used to derive the default DNs.
        type: str
    search_base:
        description: Search base DN for absent; defaults to the domain.
        type: str
    verify:
        description: Bind as the user with the new password after a push.
        type: bool
        default: True
'''

EXAMPLES = '''
- name: Push an AD account over LDAPS
  ad_ldap_account:
    login_host: dc01.example.com
    login_user: jms-pam@example.com
    login_password: secret
    domain_name: example.com
    ou: OU=Staff,DC=example,DC=com
    groups: Staff-RDP
    name: alice
    password: NewPassword

- name: Disable an AD account
  ad_ldap_account:
    login_host: dc01.example.com
    login_user: jms-pam@example.com
    login_password: secret
    domain_name: example.com
    name: alice
    state: absent
    disable_only: true
'''

RETURN = '''
user_dn:
  description: The distinguished name of the user.
  returned: when the user exists or was created
  type: str
created:
  description: Whether the user was created (present).
  returned: always
  type: bool
action:
  description: created, updated, deleted, disabled or absent.
  returned: always
  type: str
groups_added:
  description: Groups the user was added to by this run.
  returned: present
  type: list
auth_status:
  description: Result of verifying the pushed password with a fresh bind.
  returned: present
  type: str
reason_code:
  description: A stable classification for the result.
  returned: always
  type: str
change_succeeded:
  description: Whether AD accepted the push.
  returned: present
  type: bool
'''

from ansible.module_utils.basic import AnsibleModule, missing_required_lib

from libs.ansible.modules_utils.ad_ldap import (
    HAS_LDAP3,
    PROTECTION_ATTRIBUTES,
    ADLdapClient,
    ADLdapError,
    connection_argument_spec,
    domain_to_base_dn,
    first_value,
    is_protected_entry,
    split_names,
    user_identity,
)


def argument_spec():
    options = connection_argument_spec()
    options.update(
        name=dict(type='str', required=True),
        password=dict(type='str', required=False, default='', no_log=True),
        state=dict(type='str', required=False, default='present',
                   choices=['present', 'absent']),
        ou=dict(type='str', required=False, default=''),
        groups=dict(type='str', required=False, default=''),
        disable_only=dict(type='bool', required=False, default=False),
        domain_name=dict(type='str', required=False, default=''),
        search_base=dict(type='str', required=False, default=''),
        verify=dict(type='bool', required=False, default=True),
    )
    return options


def find_existing(client, conn, params, attributes=None):
    try:
        return client.find_user_entry(
            conn, params['name'], domain_name=params['domain_name'],
            search_base=params['search_base'], attributes=attributes,
        )
    except ADLdapError as error:
        if error.reason_code == 'USER_NOT_FOUND':
            return None
        raise


def push_account(module, client):
    params = dict(module.params)
    if not params['password']:
        raise ADLdapError('A password is required to push an account', 'PASSWORD_REQUIRED')
    domain_dn = domain_to_base_dn(params['domain_name'])
    ou = params['ou'].strip()
    container = ou or ('CN=Users,%s' % domain_dn if domain_dn else '')
    if not container:
        raise ADLdapError(
            'An organizational unit is required when the directory service has '
            'no domain name', 'OU_REQUIRED',
        )
    # Existing users are only looked up where new ones would be created, so a
    # push never resets an unrelated account elsewhere in the domain.
    params['search_base'] = ou

    conn = client.bind(params['login_user'], params['login_password'])
    try:
        # Resolve groups before changing anything, so a typo fails cleanly.
        group_base = domain_dn or container
        group_dns = [
            client.find_group(conn, group, group_base)
            for group in split_names(params['groups'])
        ]
        entry = find_existing(client, conn, params)
        if module.check_mode:
            return {
                'user_dn': entry['dn'] if entry else None,
                'created': entry is None,
                'action': 'updated' if entry else 'created',
                'groups_added': [],
            }, False

        if entry is None:
            sam, upn = user_identity(params['name'], params['domain_name'])
            user_dn = client.create_user(conn, container, sam, upn, params['password'])
            action = 'created'
        else:
            user_dn = entry['dn']
            client.set_password(conn, user_dn, params['password'])
            action = 'updated'
        groups_added = client.add_to_groups(conn, user_dn, group_dns)
    finally:
        client.unbind(conn)
    return {
        'user_dn': user_dn,
        'created': action == 'created',
        'action': action,
        'groups_added': groups_added,
    }, True


def remove_account(module, client):
    params = module.params
    conn = client.bind(params['login_user'], params['login_password'])
    try:
        entry = find_existing(client, conn, params, attributes=PROTECTION_ATTRIBUTES)
        if entry is None:
            return {'action': 'absent', 'created': False}, False
        attributes = entry.get('attributes') or {}
        user_dn = entry['dn']
        if is_protected_entry(attributes):
            raise ADLdapError(
                'Refusing to remove protected account %s (adminCount=1 or a '
                'critical system object)' % user_dn, 'PROTECTED_ACCOUNT',
            )
        target_sam = str(first_value(attributes, 'sAMAccountName') or '')
        login_sam = client.get_login_sam(conn) or user_identity(params['login_user'])[0]
        if target_sam and login_sam and target_sam.lower() == login_sam.lower():
            raise ADLdapError(
                'Refusing to remove the account used to run this automation: %s' % user_dn,
                'LOGIN_ACCOUNT',
            )
        result = {'user_dn': user_dn, 'created': False}
        if params['disable_only']:
            if module.check_mode:
                return dict(result, action='disabled'), False
            changed = client.disable_user(
                conn, user_dn, first_value(attributes, 'userAccountControl')
            )
            return dict(result, action='disabled'), changed
        if module.check_mode:
            return dict(result, action='deleted'), False
        client.delete_user(conn, user_dn)
        return dict(result, action='deleted'), True
    finally:
        client.unbind(conn)


def main():
    module = AnsibleModule(argument_spec=argument_spec(), supports_check_mode=True)
    if not HAS_LDAP3:
        module.fail_json(msg=missing_required_lib('ldap3'))

    params = module.params
    present = params['state'] == 'present'
    # "unknown" is reserved for an inconclusive verification, which the push
    # manager records as unverified.
    result = {'changed': False, 'created': False, 'reason_code': ''}
    if present:
        result.update(auth_status='not_checked', change_succeeded=False)
    try:
        client = ADLdapClient.from_params(params)
        if present:
            data, changed = push_account(module, client)
        else:
            data, changed = remove_account(module, client)
    except ADLdapError as error:
        result.update(reason_code=error.reason_code, msg=str(error))
        module.fail_json(**result)

    result.update(data, changed=changed)
    if not present:
        module.exit_json(**result)

    result['change_succeeded'] = changed
    if module.check_mode or not params['verify']:
        module.exit_json(**result)

    auth_status, reason_code, message = client.check_password(
        data['user_dn'], params['password']
    )
    result.update(auth_status=auth_status, reason_code=reason_code)
    if auth_status == 'accepted':
        module.exit_json(**result)

    result['msg'] = 'Account pushed, but verification failed: %s' % message
    if auth_status == 'rejected':
        module.fail_json(**result)
    # AD accepted the push authoritatively; keep it and mark it unverified.
    result['sync_candidate'] = True
    module.exit_json(**result)


if __name__ == '__main__':
    main()
