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
from queue import Empty
from ansible.module_utils.basic import AnsibleModule
from libs.ansible.modules_utils.ssh_tunnel import TimeoutSSHTunnelForwarder


def common_argument_spec():
    options = dict(
        login_host=dict(type='str', required=False, default='localhost'),
        login_port=dict(type='int', required=False, default=22),
        login_user=dict(type='str', required=False, default='root'),
        login_password=dict(type='str', required=False, no_log=True),
        login_secret_type=dict(type='str', required=False, default='password'),
        gateway_args=dict(type='dict', required=False, default=None),
        connect_timeout=dict(type='int', required=False, default=30),
    )
    return options


class RDPConnectionManager:

    def __init__(self, module_params):
        self.params = module_params
        self.connect_timeout = max(
            int(module_params.get('connect_timeout') or 30), 1
        )
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

        tunnel = TimeoutSSHTunnelForwarder(
            (gateway_args['address'], gateway_args['port']),
            ssh_username=gateway_args['username'],
            ssh_password=gateway_args['secret'],
            ssh_pkey=gateway_args['private_key_path'],
            connect_timeout=self.connect_timeout,
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
            try:
                self.ssh_tunnel.stop(force=True)
            finally:
                self.ssh_tunnel = None

    def prepare_connection(self):
        self.setup_ssh_tunnel()

    def cleanup_connection(self):
        try:
            self.close_ssh_tunnel()
        except Exception:
            pass

    @staticmethod
    def check_rdp_connectivity(connection_details, result_queue):
        connect_params = [
            connection_details['hostname'],
            connection_details['port'],
            connection_details['username'],
            connection_details['password'],
            '',  # extra parameter (if needed)
            0  # The worker process below enforces the connection deadline.
        ]
        try:
            is_reachable = pyfreerdp.check_connectivity(*connect_params)
        except Exception as ex:
            is_reachable = False
            error_message = str(ex)
        else:
            error_message = '' if is_reachable else 'RDP connection failed'
        result_queue.put((is_reachable, error_message))

    def attempt_connection(self):
        if self.params['login_secret_type'] != 'password':
            error_message = f"Unsupported authentication method: {self.params['login_secret_type']}"
            return False, error_message

        connection_process = None
        try:
            self.prepare_connection()

            connection_process = multiprocessing.Process(
                target=self.check_rdp_connectivity,
                args=(self.connection_details, self.result_queue),
            )
            connection_process.start()
            connection_process.join(self.connect_timeout)
            if connection_process.is_alive():
                connection_process.terminate()
                connection_process.join(1)
                if connection_process.is_alive() and hasattr(connection_process, 'kill'):
                    connection_process.kill()
                    connection_process.join(1)
                return False, (
                    'RDP connection timed out after %s seconds'
                    % self.connect_timeout
                )

            try:
                is_reachable, error_message = self.result_queue.get(timeout=1)
            except Empty:
                return False, 'RDP connectivity process returned no result'

            if not is_reachable:
                return False, error_message or 'RDP connection failed'
        except Exception as ex:
            return False, str(ex)
        finally:
            if connection_process and connection_process.is_alive():
                connection_process.terminate()
                connection_process.join(1)
            self.cleanup_connection()
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
