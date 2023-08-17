#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = '''
---
module: custom_command
short_description: Adds or removes a user with custom commands by ssh
description:
    - You can add or edit users using ssh with custom commands.

options:
  protocol:
    default: ssh
    choices: [ssh]
    description:
      - C(ssh) The remote asset is connected using ssh.
    type: str
  name:
    description:
      - The name of the user to add or remove.
    required: true
    aliases: [user]
    type: str
  password:
    description:
      - The password to use for the user.
    type: str
    aliases: [pass]
  commands:
    description:
      - Custom change password commands.
    type: list
    required: true
  first_conn_delay_time:
    description:
      - Delay for executing the command after SSH connection(unit: s)
    type: float
    required: false
'''

EXAMPLES = '''
- name: Create user with name 'jms' and password '123456'.
  custom_command:
    login_host: "localhost"
    login_port: 22
    login_user: "admin"
    login_password: "123456"
    name: "jms"
    password: "123456"
    commands: ['passwd {username}', '{password}', '{password}']
'''

RETURN = '''
name:
    description: The name of the user to add.
    returned: success
    type: str
'''

from ansible.module_utils.basic import AnsibleModule

from ops.ansible.modules_utils.custom_common import (
    SSHClient, common_argument_spec
)


def get_commands(module):
    username = module.params['name']
    password = module.params['password']
    commands = module.params['commands'] or []
    login_password = module.params['login_password']
    for index, command in enumerate(commands):
        commands[index] = command.format(
            username=username, password=password, login_password=login_password
        )
    return commands

# =========================================
# Module execution.
#


def main():
    argument_spec = common_argument_spec()
    argument_spec.update(
        name=dict(required=True, aliases=['user']),
        password=dict(aliases=['pass'], no_log=True),
        commands=dict(type='list', required=False),
    )
    module = AnsibleModule(argument_spec=argument_spec)

    ssh_client = SSHClient(module)
    commands = get_commands(module)
    if not commands:
        module.fail_json(
            msg='No command found, please go to the platform details to add'
        )
    output, err_msg = ssh_client.execute(commands)
    if err_msg:
        module.fail_json(
            msg='There was a problem executing the command: %s' % err_msg
        )

    user = module.params['name']
    module.exit_json(changed=True, user=user)


if __name__ == '__main__':
    main()
