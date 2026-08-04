#!/usr/bin/python

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = '''
---
module: ssh_ping
short_description: Use ssh to probe whether an asset is connectable
description:
    - Use ssh to probe whether an asset is connectable.
options:
    login_host:
        description: The target host to connect.
        type: str
        required: True
    login_port:
        description: The port on the target host.
        type: int
        required: False
        default: 22
    login_user:
        description: The username for the SSH connection.
        type: str
        required: True
    login_password:
        description: The password for the SSH connection.
        type: str
        required: True
        no_log: True
    auth_only:
        description:
            - Stop after a fresh SSH authentication succeeds.
            - Accounts reached through su, sudo, or device privilege switching
              still require the shell phase.
        type: bool
        required: False
        default: False
    fail_on_unknown:
        description:
            - Fail when transport, gateway, timeout, or shell errors make the
              credential result inconclusive.
        type: bool
        required: False
        default: True
    change_succeeded:
        description:
            - Whether the remote secret change step completed successfully.
            - Returned with the probe so callers can decide whether an
              inconclusive verification is safe to synchronize locally.
        type: bool
        required: False
        default: True
'''

EXAMPLES = '''
- name: Ping asset server using SSH.
  ssh_ping:
    login_host: 127.0.0.1
    login_port: 22
    login_user: jms
    login_password: password
'''

RETURN = '''
is_available:
  description: Indicate whether the target server is reachable via SSH.
  returned: always
  type: bool
  sample: true
auth_status:
  description: Whether the supplied credential was accepted, rejected, or could not be verified.
  returned: always
  type: str
  sample: accepted
reason_code:
  description: A stable classification for the probe result.
  returned: always
  type: str
  sample: AUTHENTICATION_ACCEPTED
change_succeeded:
  description: Whether the preceding remote secret change step succeeded.
  returned: always
  type: bool
  sample: true
'''

import socket

import paramiko
from ansible.module_utils.basic import AnsibleModule
from libs.ansible.modules_utils.remote_client import (
    BecomeAuthenticationError,
    SSHClient,
    common_argument_spec,
)


def classify_probe_error(error, become=False):
    if isinstance(error, BecomeAuthenticationError):
        return 'rejected', 'TARGET_AUTHENTICATION_FAILED'
    if isinstance(error, paramiko.BadAuthenticationType):
        return 'unknown', 'AUTH_METHOD_UNAVAILABLE'
    if isinstance(error, paramiko.ssh_exception.PartialAuthentication):
        return 'unknown', 'ADDITIONAL_AUTH_REQUIRED'
    if isinstance(error, paramiko.PasswordRequiredException):
        return 'unknown', 'PRIVATE_KEY_PASSPHRASE_REQUIRED'
    if isinstance(error, paramiko.AuthenticationException):
        if become:
            # SSH authenticated the source account, so its failure says
            # nothing conclusive about the target privilege credential.
            return 'unknown', 'PRIVILEGED_AUTH_FAILED'
        return 'rejected', 'AUTHENTICATION_FAILED'
    if isinstance(error, (socket.timeout, TimeoutError)):
        return 'unknown', 'SSH_TIMEOUT'
    if isinstance(error, paramiko.ssh_exception.NoValidConnectionsError):
        return 'unknown', 'CONNECTION_FAILED'
    if isinstance(error, paramiko.SSHException):
        return 'unknown', 'SSH_PROTOCOL_ERROR'
    if isinstance(error, OSError):
        return 'unknown', 'NETWORK_OR_GATEWAY_ERROR'
    return 'unknown', 'PROBE_ERROR'


def main():
    options = common_argument_spec()
    module = AnsibleModule(argument_spec=options, supports_check_mode=True)

    result = {
        'changed': False,
        'is_available': False,
        'auth_status': 'unknown',
        'reason_code': '',
        'change_succeeded': module.params['change_succeeded'],
    }

    try:
        with SSHClient(module) as client:
            client.connect(
                auth_only=module.params['auth_only'],
                raise_on_error=True,
            )
    except Exception as error:
        auth_status, reason_code = classify_probe_error(
            error, become=module.params['become']
        )
        result.update(
            auth_status=auth_status,
            reason_code=reason_code,
            msg=str(error),
        )
        if auth_status == 'rejected' or module.params['fail_on_unknown']:
            module.fail_json(**result)
        module.exit_json(**result)

    result.update(
        is_available=True,
        auth_status='accepted',
        reason_code='AUTHENTICATION_ACCEPTED',
    )
    module.exit_json(**result)


if __name__ == '__main__':
    main()
