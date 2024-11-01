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
    type: str
    required: true
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
    commands: 'passwd {username}\n{password}\n{password}']
'''

RETURN = '''
name:
    description: The name of the user to add.
    returned: success
    type: str
'''

from ansible.module_utils.basic import AnsibleModule

from libs.ansible.modules_utils.remote_client import (
    SSHClient, common_argument_spec
)


def get_commands_and_answers(module) -> (list, list):
    username = module.params['name']
    password = module.params['password']
    commands = module.params['commands'] or ''
    answers = module.params['answers'] or ''
    login_password = module.params['login_password']

    if isinstance(commands, list):
        commands = '\n'.join(commands)
    commands = commands.format(
        username=username, password=password, login_password=login_password
    )
    return commands.split('\n'), answers.split('\n')


# =========================================
# Module execution.
#


def main():
    argument_spec = common_argument_spec()
    argument_spec.update(
        name=dict(required=True, aliases=['user']),
        password=dict(aliases=['pass'], no_log=True),
    )
    module = AnsibleModule(argument_spec=argument_spec)

    commands, answers = get_commands_and_answers(module)
    if not commands:
        module.fail_json(
            msg='No command found, please go to the platform details to add'
        )
    with SSHClient(module) as client:
        output, err_msg = client.execute(commands, answers)
        if err_msg:
            module.fail_json(
                msg='There was a problem executing the command: %s' % err_msg
            )

    user = module.params['name']
    module.exit_json(changed=True, user=user)


if __name__ == '__main__':
    main()
