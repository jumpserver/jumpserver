#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: website_ping
short_description: Use Playwright to simulate a browser for connectivity testing
description:
    - Use Playwright to simulate a browser for connectivity testing
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
- name: Ping asset server using Playwright.
  website_ping:
    login_host: 127.0.0.1
'''

RETURN = '''
is_available:
  description: Indicate whether the target server is reachable via Playwright.
  returned: always
  type: bool
  sample: true
'''

from ansible.module_utils.basic import AnsibleModule
from libs.ansible.modules_utils.web_common import WebAutomationHandler, common_argument_spec


def main():
    options = common_argument_spec()
    module = AnsibleModule(argument_spec=options, supports_check_mode=False)
    extra_infos = {
        'login_username': module.params['login_user'],
        'login_password': module.params['login_password'],
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

    result = {'changed': False, 'is_available': True}
    module.exit_json(**result)


if __name__ == '__main__':
    main()
