#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: telnet_ping
short_description: Use telnet to probe whether an asset is connectable
description:
    - Use telnet to probe whether an asset is connectable
'''

EXAMPLES = '''
- name: >
    Telnet asset server.
  telnet_ping:
    login_host: localhost
    login_port: 22
'''

RETURN = '''
is_available:
  description: Telnet server availability.
  returned: always
  type: bool
  sample: true
'''

import telnetlib

from ansible.module_utils.basic import AnsibleModule


# =========================================
# Module execution.
#

def common_argument_spec():
    options = dict(
        login_host=dict(type='str', required=False, default='localhost'),
        login_port=dict(type='int', required=False, default=22),
        timeout=dict(type='int', required=False, default=10),
    )
    return options


def main():
    options = common_argument_spec()
    module = AnsibleModule(argument_spec=options, supports_check_mode=True, )

    result = {
        'changed': False, 'is_available': True
    }
    host = module.params['login_host']
    port = module.params['login_port']
    timeout = module.params['timeout']
    try:
        client = telnetlib.Telnet(host, port, timeout=timeout)
        client.close()
    except Exception as err: # noqa
        result['is_available'] = False
        module.fail_json(msg='Unable to connect to asset: %s' % err)

    return module.exit_json(**result)


if __name__ == '__main__':
    main()
