#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: website_user
short_description: Use Playwright to simulate browser operations for users.
description:
    - Use Playwright to simulate browser operations for users, such as password change.
options:
    login_host:
        description: The target host to connect.
        type: str
        required: True
    login_user:
        description: The username for the website connection.
        type: str
        required: True
    login_password:
        description: The password for the website connection.
        type: str
        required: True
        no_log: True
    name:
        description: The name of the user to change password.
        required: true
        aliases: [user]
        type: str
    password:
        description: The password to use for the user.
        type: str
        aliases: [pass]
    timeout:
        description: Timeout period for step execution.
        type: int
        required: False
    steps:
        description: Meta-information for browser-emulated actions.
        type: list
        required: False
'''

EXAMPLES = '''
- name: Change password using Playwright.
  website_user:
    login_host: 127.0.0.1
'''

RETURN = '''
failed:
  description: Verify whether the task simulated and operated via Playwright has succeeded.
  returned: always
  type: bool
  sample: false
'''

from ansible.module_utils.basic import AnsibleModule
from libs.ansible.modules_utils.web_common import WebAutomationHandler, common_argument_spec


def main():
    argument_spec = common_argument_spec()
    argument_spec.update(
        name=dict(required=True, aliases=['user']),
        password=dict(aliases=['pass'], no_log=True),
    )
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    extra_infos = {
        'login_username': module.params['login_user'],
        'login_password': module.params['login_password'],
        'username': module.params['name'],
        'password': module.params['password'],
    }
    handler = WebAutomationHandler(
        address=module.params['login_host'],
        timeout=module.params['timeout'],
        load_state=module.params['load_state'],
        extra_infos=extra_infos,
    )
    try:
        handler.execute(steps=module.params['steps'])
    except Exception as e:
        module.fail_json(msg=str(e))

    result = {'changed': True}
    module.exit_json(**result)


if __name__ == '__main__':
    main()
