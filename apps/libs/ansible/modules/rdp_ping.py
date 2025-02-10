#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: custom_rdp_ping
short_description: Use RDP to probe whether an asset is connectable.
description:
    - Use RDP to probe whether an asset is connectable.
options:
    login_host:
        description: Target host to connect.
        type: str
        required: False
        default: localhost
    login_port:
        description: Target port to connect.
        type: int
        required: False
        default: 22
    login_user:
        description: Login user for the connection.
        type: str
        required: False
        default: root
    login_password:
        description: Login password.
        type: str
        required: False
        no_log: True
    login_secret_type:
        description: Authentication method.
        type: str
        required: False
        default: password
    gateway_args:
        description: Arguments for setting up an SSH tunnel.
        type: dict
        required: False
        default: null
'''

EXAMPLES = '''
- name: Ping asset server using RDP.
  custom_rdp_ping:
    login_host: 127.0.0.1
    login_port: 3389
    login_user: jms
    login_password: password
'''

RETURN = '''
is_available:
  description: Indicates if the Windows asset is available.
  returned: always
  type: bool
  sample: true
conn_err_msg:
  description: Connection error message (if any).
  returned: always
  type: str
  sample: ''
'''

import pyfreerdp
import multiprocessing
from sshtunnel import SSHTunnelForwarder
from ansible.module_utils.basic import AnsibleModule


def common_argument_spec():
    options = dict(
        login_host=dict(type='str', required=False, default='localhost'),
        login_port=dict(type='int', required=False, default=22),
        login_user=dict(type='str', required=False, default='root'),
        login_password=dict(type='str', required=False, no_log=True),
        login_secret_type=dict(type='str', required=False, default='password'),
        gateway_args=dict(type='dict', required=False, default=None),
    )
    return options


class RDPConnectionManager:

    def __init__(self, module_params):
        self.params = module_params
        self.ssh_tunnel = None
        self.connection_details = self.build_connection_details()
        self.result_queue = multiprocessing.Queue()

    def build_connection_details(self):
        return {
            'hostname': self.params['login_host'],
            'port': self.params['login_port'],
            'username': self.params['login_user'],
            'password': self.params['login_password']
        }

    def setup_ssh_tunnel(self):
        gateway_args = self.params['gateway_args'] or {}
        if not gateway_args:
            return

        tunnel = SSHTunnelForwarder(
            (gateway_args['address'], gateway_args['port']),
            ssh_username=gateway_args['username'],
            ssh_password=gateway_args['secret'],
            ssh_pkey=gateway_args['private_key_path'],
            remote_bind_address=(
                self.connection_details['hostname'],
                self.connection_details['port']
            )
        )
        tunnel.start()

        self.connection_details['hostname'] = '127.0.0.1'
        self.connection_details['port'] = tunnel.local_bind_port
        self.ssh_tunnel = tunnel

    def close_ssh_tunnel(self):
        if self.ssh_tunnel:
            self.ssh_tunnel.stop()

    def prepare_connection(self):
        self.setup_ssh_tunnel()

    def cleanup_connection(self):
        self.close_ssh_tunnel()

    def check_rdp_connectivity(self):
        connect_params = [
            self.connection_details['hostname'],
            self.connection_details['port'],
            self.connection_details['username'],
            self.connection_details['password'],
            '',  # extra parameter (if needed)
            0    # timeout (if needed)
        ]
        try:
            is_reachable = pyfreerdp.check_connectivity(*connect_params)
        except Exception as ex:
            is_reachable = False
        self.result_queue.put(is_reachable)

    def attempt_connection(self):
        if self.params['login_secret_type'] != 'password':
            error_message = f"Unsupported authentication method: {self.params['login_secret_type']}"
            return False, error_message

        try:
            self.prepare_connection()

            connection_process = multiprocessing.Process(
                target=self.check_rdp_connectivity
            )
            connection_process.start()
            connection_process.join()

            is_reachable = self.result_queue.get()
            self.cleanup_connection()

            if not is_reachable:
                return False, 'RDP connection failed'
        except Exception as ex:
            return False, str(ex)
        return True, ''


def main():
    argument_spec = common_argument_spec()
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    rdp_manager = RDPConnectionManager(module.params)
    is_available, error_message = rdp_manager.attempt_connection()

    # Prepare the result structure.
    result = {
        'changed': False,
        'is_available': is_available,
        'conn_err_msg': error_message
    }

    if not is_available:
        module.fail_json(msg=f"Unable to connect to asset: {error_message}", **result)
    else:
        module.exit_json(**result)


if __name__ == '__main__':
    main()
